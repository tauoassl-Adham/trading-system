import os

def generate_tree(startpath):
    for root, dirs, files in os.walk(startpath):
        # تجاهل مجلدات النظام والبيئة
        if '.git' in dirs: dirs.remove('.git')
        if 'venv' in dirs: dirs.remove('venv')
        if '__pycache__' in dirs: dirs.remove('__pycache__')
        
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print(f'{indent}📁 {os.path.basename(root)}/')
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print(f'{subindent}📄 {f}')

if __name__ == "__main__":
    generate_tree(".")