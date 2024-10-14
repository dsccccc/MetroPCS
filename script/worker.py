import re

def replacer(input_file: str = './tmp/README.md', output_file: str = 'README.md', reg: str = r'/<!-- TABLE_START -->([\s\S]*?)<!-- TABLE_END -->/'):
    with open(input_file, 'r') as f:
        data = f.read()
    with open(output_file, 'r') as f:
        table = f.read()
    data = re.sub(reg, table, data)
    with open(output_file, 'w') as f:
        f.write(table)

if __name__ == '__main__':
    from src.MetroPCS import MetroPCS
    metro = MetroPCS()
    metro.wrapper()
    replacer()
