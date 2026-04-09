---
name: files
description: File operations for creating, reading, and modifying files
---

# File Operations

## Create a New File
```bash
cat > path/to/file.ts << 'EOF'
// file contents here
EOF
```

## Append to a File
```bash
cat >> path/to/file.ts << 'EOF'
// additional content
EOF
```

## Replace Content in a File
```bash
sed -i 's/old_text/new_text/g' path/to/file.ts
```

## Read a File
```bash
cat path/to/file.ts
```

## List Directory Contents
```bash
ls -la path/to/directory
```

## Find Files
```bash
find /workspace -name "*.ts" -type f
```

## Check if File Exists
```bash
if [ -f path/to/file.ts ]; then
  echo "File exists"
fi
```
