import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
from collections import deque
import random

class QNetwork(nn.Module):
    """
    Standard fully connected Q-Network for the DQN Agent.
    Input will be the (flattened) latent state from STGNN for a specific intersection.
    """
    def __init__(self, state_size, action_size, hidden_size=64):
        super(QNetwork, self).__init__()
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, action_size)

    def forward(self, state):
        x = F.relu(self.fc1(state))
        x = F.relu(self.fc2(x))
        return self.fc3(x)

class ReplayBuffer:
    def __init__(self, capacity):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size):
        state, action, reward, next_state, done = zip(*random.sample(self.buffer, batch_size))
        return (torch.FloatTensor(np.array(state)), 
                torch.LongTensor(action).unsqueeze(1), 
                torch.FloatTensor(reward).unsqueeze(1), 
                torch.FloatTensor(np.array(next_state)), 
                torch.FloatTensor(done).unsqueeze(1))
    
    def __len__(self):
        return len(self.buffer)

class DQNAgent:
    """
    DQN Agent capable of handling independent Q-learning for each intersection or
    centralized learning depending on state formulation.
    """
    def __init__(self, state_size, action_size, config):
        self.action_size = action_size
        self.gamma = config.get("gamma", 0.99)
        self.tau = config.get("tau", 0.005)
        self.batch_size = config.get("batch_size", 64)
        
        self.epsilon = config.get("epsilon_start", 1.0)
        self.epsilon_min = config.get("epsilon_end", 0.05)
        self.epsilon_decay = config.get("epsilon_decay", 10000)
        self.steps_done = 0
        
        # Policy Network & Target Network
        self.policy_net = QNetwork(state_size, action_size)
        self.target_net = QNetwork(state_size, action_size)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=config.get("learning_rate", 1e-4))
        self.memory = ReplayBuffer(config.get("buffer_size", 50000))
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.policy_net.to(self.device)
        self.target_net.to(self.device)

    def select_action(self, state):
        """ Epsilon-Greedy Action Selection """
        self.steps_done += 1
        # Decay Epsilon
        self.epsilon = max(self.epsilon_min, self.epsilon - (1.0 / self.epsilon_decay))
        
        if random.random() > self.epsilon:
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
                q_values = self.policy_net(state_tensor)
                return q_values.argmax().item()
        else:
            return random.randrange(self.action_size)

    def step(self, state, action, reward, next_state, done):
        """ Store experience and trigger learning """
        self.memory.push(state, action, reward, next_state, done)
        if len(self.memory) > self.batch_size:
            self.learn()

    def learn(self):
        states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)
        
        states = states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        next_states = next_states.to(self.device)
        dones = dones.to(self.device)

        # Get max predicted Q values for next states from target model
        next_q_targets = self.target_net(next_states).max(1)[0].unsqueeze(1)
        # Compute Q targets for current states
        q_targets = rewards + (self.gamma * next_q_targets * (1 - dones))

        # Get expected Q values from policy model
        q_expected = self.policy_net(states).gather(1, actions)

        # Compute loss
        loss = F.mse_loss(q_expected, q_targets)

        # Minimize the loss
        self.optimizer.zero_grad()
        loss.backward()
        # Gradient clipping to prevent exploding loss
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1)
        self.optimizer.step()

        # Update target network via soft update or hard periodically
        self.soft_update(self.policy_net, self.target_net, self.tau)

    def soft_update(self, local_model, target_model, tau):
        """Soft update target model parameters."""
        for target_param, local_param in zip(target_model.parameters(), local_model.parameters()):
            target_param.data.copy_(tau*local_param.data + (1.0-tau)*target_param.data)
