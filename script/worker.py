def replacer(table: str, input_file: str = './tmp/README.md', output_file: str = 'README.md', reg: str = '<!-- TABLE_START --><!-- TABLE_END -->'):
    if not table.strip():
        raise ValueError('Refusing to replace the product table with empty output')
    with open(input_file, 'r', encoding='utf-8') as f:
        data = f.read()
    data = data.replace(reg, table)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(data)

if __name__ == '__main__':
    from src.MetroPCS import MetroPCS
    metro = MetroPCS()
    metro.wrapper()
    replacer(metro.markdown)
