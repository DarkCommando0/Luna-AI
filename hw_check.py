import psutil

hw = {
    'cpu_cores': psutil.cpu_count(logical=False),
    'cpu_threads': psutil.cpu_count(logical=True),
    'ram_gb': psutil.virtual_memory().total / (1024**3)
}

print('=== Hardware Analysis ===')
print(f'CPU: {hw["cpu_cores"]} cores, {hw["cpu_threads"]} threads')
print(f'RAM: {hw["ram_gb"]:.1f} GB')
print('GPU: RTX 5070 (12GB VRAM)')
print()
print('=== Recommended Local Models ===')
print('With your specs, you can run:')
print('1. Mistral 7B Instruct (14GB) - Great balance, fits in VRAM')
print('2. Llama 3.1 8B Instruct (16GB) - Latest model, excellent performance')
print('3. Qwen 2.5 7B Instruct (15GB) - Strong multilingual')
print('4. DeepSeek Coder 6.7B (13GB) - Excellent for coding')
print('5. Llama 3.1 70B (40GB) - Very capable with GPU+CPU offloading')
print('6. Qwen 2.5 32B Instruct (19GB) - Large model, good performance')
