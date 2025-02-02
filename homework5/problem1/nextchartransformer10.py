
# In[0]
import torch
import time
import torch.nn as nn
import torch.optim as optim
import numpy as np
from sklearn.model_selection import train_test_split
import torchinfo    


device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

with open('/home/csalitre/school/ecgr-5106/intro-to-deeplearning/Datasets/sample_data.txt', 'r') as file:
    text = file.read()

# Creating character vocabulary
chars = sorted(list(set(text)))
ix_to_char = {i: ch for i, ch in enumerate(chars)}
char_to_ix = {ch: i for i, ch in enumerate(chars)}

# Preparing the dataset for sequence predictiona
X = []
y = []
max_length = 10  # Maximum length of input sequences
for i in range(len(text) - max_length - 1):
    sequence = text[i:i + max_length]
    label_sequence = text[i+1:i + max_length + 1]  # Shift by one for the next character sequence
    X.append([char_to_ix[char] for char in sequence])
    y.append([char_to_ix[char] for char in label_sequence])

X = np.array(X)
y = np.array(y)

# Splitting the dataset into training and validation sets
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

# Converting data to PyTorch tensors
X_train = torch.tensor(X_train, dtype=torch.long).to(device)
y_train = torch.tensor(y_train, dtype=torch.long).to(device)
X_val = torch.tensor(X_val, dtype=torch.long).to(device)
y_val = torch.tensor(y_val, dtype=torch.long).to(device)

# Positional Encoding
class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=5000):
        super(PositionalEncoding, self).__init__()
        self.encoding = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        self.encoding[:, 0::2] = torch.sin(position * div_term)
        self.encoding[:, 1::2] = torch.cos(position * div_term)
        self.encoding = self.encoding.unsqueeze(0)

    def forward(self, x):
        self.encoding = self.encoding.to(device)
        return x + self.encoding[:, :x.size(1)].detach()

# Defining the Transformer model
class CharTransformer(nn.Module):
    def __init__(self, input_size, hidden_size, output_size, num_layers, nhead):
        super(CharTransformer, self).__init__()
        self.embedding = nn.Embedding(input_size, hidden_size)
        self.pos_encoder = PositionalEncoding(hidden_size)
        encoder_layers = nn.TransformerEncoderLayer(hidden_size, nhead, batch_first=True)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layers, num_layers)
        self.fc = nn.Linear(hidden_size, output_size)
        self.softmax = nn.Softmax(dim=2)  # Softmax layer over the feature dimension

    def forward(self, x):
        embedded = self.embedding(x)
        embedded = self.pos_encoder(embedded)
        transformer_output = self.transformer_encoder(embedded)
        output = self.fc(transformer_output)
        return self.softmax(output)  # Apply softmax to the linear layer output


# Hyperparameters
hidden_size = 16
num_layers = 3
nhead = 2
learning_rate = 0.001
epochs = 100

# Model, loss, and optimizer
model = CharTransformer(len(chars), hidden_size, len(chars), num_layers, nhead).to(device)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=learning_rate)

summary = torchinfo.summary(model, input_data=X_train)
print(summary)

# In[1]

total_start_time = time.time()
# Training the model
for epoch in range(epochs):
    start_time = time.time()
    model.train()
    optimizer.zero_grad()
    output = model(X_train)
    loss = criterion(output.transpose(1, 2), y_train)  # Reshape output to match the CrossEntropyLoss expectations
    loss.backward()
    optimizer.step()

    # Validation
    model.eval()
    with torch.no_grad():
        val_output = model(X_val)
        val_loss = criterion(val_output.transpose(1, 2), y_val)  # Same transpose for validation
        _, predicted = torch.max(val_output, 2)  # Adjust dimension for prediction
        val_accuracy = (predicted == y_val).float().mean()  # Calculate accuracy

    if (epoch+1) % 10 == 0:
        end_time = time.time()
        print(f'Epoch {epoch+1}, Loss: {loss.item()}, Validation Loss: {val_loss.item()}, Validation Accuracy: {val_accuracy.item()}')
total_end_time = time.time()
total_execution_time =  total_end_time - total_start_time
print(f'Total execution time: {total_execution_time} seconds')

# In[2]

# Prediction function7
def predict_next_char(model, char_to_ix, ix_to_char, initial_str):
    model.to(device)
    model.eval()
    with torch.no_grad():
        initial_input = torch.tensor([char_to_ix[c] for c in initial_str[-max_length:]], dtype=torch.long).unsqueeze(0).to(device)
        prediction = model(initial_input)
        #print("Prediction shape:", prediction.shape)
        last_timestep_pred = prediction.squeeze(0)[-1]
        predicted_index = torch.argmax(last_timestep_pred, dim=0).item()
        return ix_to_char[predicted_index]


# Predicting the next character
test_str = "This is a simple example to demonstrate ho"
predicted_char = predict_next_char(model, char_to_ix, ix_to_char, test_str)
print(f"Predicted next character: '{predicted_char}'")
# %%
