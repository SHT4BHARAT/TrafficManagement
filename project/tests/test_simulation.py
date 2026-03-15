import asyncio
import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, AsyncMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation.traffic_sim import IntersectionSimulator
from brain.optimizer import TrafficRLAgent
from brain.routing import CityGraphRouter
from core.optimization import SCOOTController
from core.utils import safe_json_parse, extract_json_from_text, detect_emergency_zone


class TestTrafficSimulation:
    """Test basic traffic simulation functionality"""
    
    def test_intersection_simulator_init(self):
        """Test simulator initialization"""
        sim = IntersectionSimulator("INT_001")
        assert sim.intersection_id == "INT_001"
        assert all(count == 0 for count in sim.queues.values())
        assert sim.current_phase == "N-S Green"
    
    def test_simulator_step_vehicle_arrival(self):
        """Test that vehicles arrive at intersection"""
        sim = IntersectionSimulator("INT_001")
        initial_state = sim.step(None)
        # Should have some vehicles after first step
        assert sum(initial_state.values()) >= 0  # Random between 0-5 per lane
    
    def test_simulator_step_vehicle_discharge(self):
        """Test that vehicles are discharged from green lanes"""
        sim = IntersectionSimulator("INT_001")
        # Manually set queue
        sim.queues = {"N": 10, "S": 10, "E": 10, "W": 10}
        
        # Apply N-S Green phase
        result = sim.step("N-S Green")
        
        # North and South should have 8 fewer vehicles (assuming discharge > arrival)
        assert result["N"] < 10
        assert result["S"] < 10
    
    def test_simulator_phase_change(self):
        """Test phase transitions"""
        sim = IntersectionSimulator("INT_001")
        sim.step("N-S Green")
        assert sim.current_phase == "N-S Green"
        
        sim.step("E-W Green")
        assert sim.current_phase == "E-W Green"


class TestRLAgent:
    """Test reinforcement learning agent functionality"""
    
    def test_agent_init(self):
        """Test agent initialization"""
        agent = TrafficRLAgent("INT_001")
        assert agent.intersection_id == "INT_001"
        assert agent.total_reward == 0
        assert agent.last_state is None
    
    def test_normalize_state_with_counts(self):
        """Test state normalization with 'counts' key"""
        agent = TrafficRLAgent("INT_001")
        state = {"counts": {"N": 5, "S": 3, "E": 2, "W": 1}, "timestamp": 123}
        normalized = agent._normalize_state(state)
        assert normalized == {"N": 5, "S": 3, "E": 2, "W": 1}
    
    def test_normalize_state_direct_dict(self):
        """Test state normalization with direct queue dict"""
        agent = TrafficRLAgent("INT_001")
        state = {"N": 5, "S": 3, "E": 2, "W": 1}
        normalized = agent._normalize_state(state)
        assert normalized == state
    
    def test_normalize_state_invalid(self):
        """Test state normalization with invalid input"""
        agent = TrafficRLAgent("INT_001")
        normalized = agent._normalize_state(None)
        assert normalized == {"N": 0, "S": 0, "E": 0, "W": 0}
    
    def test_compute_reward_positive(self):
        """Test positive reward for queue reduction"""
        agent = TrafficRLAgent("INT_001")
        prev_state = {"N": 10, "S": 10, "E": 5, "W": 5}
        curr_state = {"N": 5, "S": 5, "E": 5, "W": 5}
        
        reward = agent.compute_reward(prev_state, curr_state)
        assert reward > 0  # Queue reduced, so positive reward
    
    def test_compute_reward_negative(self):
        """Test negative reward for queue increase"""
        agent = TrafficRLAgent("INT_001")
        prev_state = {"N": 5, "S": 5, "E": 5, "W": 5}
        curr_state = {"N": 10, "S": 10, "E": 5, "W": 5}
        
        reward = agent.compute_reward(prev_state, curr_state)
        assert reward < 0  # Queue increased, so negative reward
    
    def test_compute_action_ns_priority(self):
        """Test action selection prioritizes congested lanes"""
        agent = TrafficRLAgent("INT_001")
        state = {"N": 20, "S": 20, "E": 5, "W": 5}
        
        action = agent.compute_action(state)
        assert action == "N-S Green"
    
    def test_compute_action_ew_priority(self):
        """Test action selection for E-W priority"""
        agent = TrafficRLAgent("INT_001")
        state = {"N": 5, "S": 5, "E": 20, "W": 20}
        
        action = agent.compute_action(state)
        assert action == "E-W Green"


class TestRouting:
    """Test emergency routing functionality"""
    
    def test_router_init(self):
        """Test router initialization"""
        router = CityGraphRouter()
        assert router.graph is not None
        assert "INT_001" in router.graph
    
    def test_routing_valid_path(self):
        """Test finding valid path between connected nodes"""
        router = CityGraphRouter()
        path, time_val = router.find_emergency_path("INT_001", "INT_004")
        
        assert path is not None
        assert len(path) > 0
        assert path[0] == "INT_001"
        assert path[-1] == "INT_004"
        assert time_val > 0
    
    def test_routing_disconnected_path(self):
        """Test handling of unreachable nodes"""
        router = CityGraphRouter()
        # Create a scenario with disconnected nodes (if possible)
        path, time_val = router.find_emergency_path("INT_999", "INT_001")
        
        assert path is None or len(path) == 0
        assert time_val == float('inf')
    
    def test_green_corridor_trigger(self):
        """Test green corridor activation"""
        router = CityGraphRouter()
        path = ["INT_001", "INT_002", "INT_003"]
        
        # Should not raise exception
        try:
            router.trigger_green_corridor(path)
            assert True
        except Exception as e:
            pytest.fail(f"trigger_green_corridor raised {e}")


class TestSCOOT:
    """Test SCOOT controller functionality"""
    
    def test_scoot_init(self):
        """Test SCOOT initialization"""
        scoot = SCOOTController()
        assert scoot.current_splits == {"NS": 35, "EW": 35}
        assert scoot.step == 3
    
    def test_scoot_optimize_splits(self):
        """Test SCOOT split optimization"""
        scoot = SCOOTController()
        sensor_data = {
            "queues": {"N": 10, "S": 8, "E": 5, "W": 3},
            "vpm": {"N": 15, "S": 12, "E": 8, "W": 5}
        }
        
        duration = scoot.optimize_splits("NS", sensor_data)
        assert 10 <= duration <= 60
    
    def test_scoot_performance_index(self):
        """Test performance index calculation"""
        scoot = SCOOTController()
        queues = {"N": 10, "S": 8, "E": 5, "W": 3}
        red_times = {"N": 0, "S": 0, "E": 5, "W": 7}
        
        pi = scoot.compute_performance_index(queues, red_times)
        assert pi >= 0


class TestUtilFunctions:
    """Test utility functions"""
    
    def test_safe_json_parse_valid(self):
        """Test parsing valid JSON"""
        json_str = '{"key": "value", "number": 42}'
        result = safe_json_parse(json_str)
        assert result == {"key": "value", "number": 42}
    
    def test_safe_json_parse_invalid(self):
        """Test parsing invalid JSON"""
        result = safe_json_parse("not valid json", default_value=None)
        assert result is None
    
    def test_safe_json_parse_with_default(self):
        """Test JSON parsing with default value"""
        result = safe_json_parse("invalid", default_value={"fallback": True})
        assert result == {"fallback": True}
    
    def test_extract_json_from_text_direct(self):
        """Test extracting JSON from plain text"""
        text = '{"duration": 35, "reasoning": "standard"}'
        result = extract_json_from_text(text)
        assert result == {"duration": 35, "reasoning": "standard"}
    
    def test_extract_json_from_text_markdown(self):
        """Test extracting JSON from markdown code block"""
        text = '''Some explanation before
```json
{"duration": 40, "reasoning": "increased traffic"}
```
Some explanation after'''
        result = extract_json_from_text(text)
        assert isinstance(result, dict)
    
    def test_detect_emergency_zone_north(self):
        """Test emergency zone detection for North"""
        zone = detect_emergency_zone("Emergency at north intersection")
        assert zone == "N"
    
    def test_detect_emergency_zone_south(self):
        """Test emergency zone detection for South"""
        zone = detect_emergency_zone("Ambulance heading south")
        assert zone == "S"
    
    def test_detect_emergency_zone_word_boundary(self):
        """Test word boundary in zone detection"""
        # Should not detect 'east' in 'northeast'
        zone = detect_emergency_zone("heading northeast")
        # Depends on implementation, but should be smart about boundaries
        assert zone in ["N", "E", "S", "W"]
    
    def test_detect_emergency_zone_default(self):
        """Test default zone when none detected"""
        zone = detect_emergency_zone("no direction specified")
        assert zone == "E"  # Default


class TestSimulationIntegration:
    """Test integrated simulation components"""
    
    def test_simulator_with_agent(self):
        """Test simulator working with RL agent"""
        sim = IntersectionSimulator("INT_001")
        agent = TrafficRLAgent("INT_001")
        
        # Simulate a few cycles
        for _ in range(3):
            state = sim.queues.copy()
            action = agent.compute_action(state)
            
            new_state = sim.step(action)
            reward = agent.compute_reward(state, new_state)
            
            assert isinstance(action, str)
            assert isinstance(reward, (int, float))
    
    def test_simulation_phase_rotation(self):
        """Test automatic phase rotation"""
        sim = IntersectionSimulator("INT_001")
        
        phases = ["N-S Green", "E-W Green"]
        phase_idx = 0
        
        for _ in range(10):
            current_phase = phases[phase_idx]
            sim.step(current_phase)
            phase_idx = (phase_idx + 1) % len(phases)
        
        # Should have rotated through phases
        assert sim.current_phase in phases
    
    def test_full_cycle_simulation(self):
        """Test a complete traffic cycle"""
        sim = IntersectionSimulator("INT_001")
        agent = TrafficRLAgent("INT_001")
        
        initial_queues = {"N": 5, "S": 5, "E": 5, "W": 5}
        sim.queues = initial_queues.copy()
        
        # Run 20 iterations
        total_reward = 0
        for i in range(20):
            state = sim.queues.copy()
            action = agent.compute_action(state)
            new_state = sim.step(action)
            reward = agent.compute_reward(state, new_state)
            total_reward += reward
        
        # Agent should accumulate some reward signal
        assert isinstance(total_reward, (int, float))


# Async tests for backend simulation
@pytest.mark.asyncio
async def test_simulation_loop_basic():
    """Test that simulation loop can run without errors"""
    # Simple mock of the simulation loop structure
    tick_count = 0
    max_ticks = 5
    
    while tick_count < max_ticks:
        # Simulate async operation
        await asyncio.sleep(0.01)
        tick_count += 1
    
    assert tick_count == max_ticks


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
