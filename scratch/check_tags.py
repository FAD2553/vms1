import re

file_path = r'C:\Users\ousmanek\Desktop\STAGE\vms1\templates\core\dashboard.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

if_tags = re.findall(r'\{%\s*if\s+', content)
endif_tags = re.findall(r'\{%\s*endif\s*%\}', content)
block_tags = re.findall(r'\{%\s*block\s+', content)
endblock_tags = re.findall(r'\{%\s*endblock\s*%\}', content)

print(f"IF tags: {len(if_tags)}")
print(f"ENDIF tags: {len(endif_tags)}")
print(f"BLOCK tags: {len(block_tags)}")
print(f"ENDBLOCK tags: {len(endblock_tags)}")

# Find the first mismatch
stack = []
lines = content.splitlines()
for i, line in enumerate(lines, 1):
    # This is a very simple parser, won't handle multiple tags on one line perfectly but should help
    tags = re.findall(r'\{%\s*(if|endif|block|endblock)\b', line)
    for tag in tags:
        if tag == 'if':
            stack.append(('if', i))
        elif tag == 'endif':
            if not stack or stack[-1][0] != 'if':
                print(f"Found endif at line {i} but no matching if. Current stack: {stack}")
            else:
                stack.pop()
        elif tag == 'block':
            stack.append(('block', i))
        elif tag == 'endblock':
            if not stack or stack[-1][0] != 'block':
                print(f"Found endblock at line {i} but no matching block. Current stack: {stack}")
            else:
                stack.pop()

if stack:
    print(f"Unclosed tags: {stack}")
