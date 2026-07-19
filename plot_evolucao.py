import pandas as pd
import matplotlib.pyplot as plt

# Carrega o histórico salvo pelo Monstro
df = pd.read_csv("historico_evolucao.csv", names=["data", "reward_medio", "taxa_acerto"])
df["data"] = pd.to_datetime(df["data"])

plt.figure(figsize=(14, 6))

plt.subplot(1, 2, 1)
plt.plot(df["data"], df["reward_medio"], marker='o')
plt.title("Evolução do Reward Médio")
plt.xlabel("Data/Hora")
plt.ylabel("Reward Médio")
plt.grid(True)

plt.subplot(1, 2, 2)
plt.plot(df["data"], df["taxa_acerto"], marker='o', color='orange')
plt.title("Evolução da Taxa de Acerto (%)")
plt.xlabel("Data/Hora")
plt.ylabel("Taxa de Acerto (%)")
plt.grid(True)

plt.tight_layout()
plt.show()