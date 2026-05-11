# 软链接的原理和实现

这篇笔记用于理解本项目为什么使用软链接，以及软链接如何创建、查看、删除和排查问题。

## 1. 什么是软链接

软链接英文叫 symbolic link，简称 symlink。

你可以先把它理解成：

```text
文件系统里的快捷方式
```

例如项目里有：

```text
data/raw/mmdocir/MMDocIR_pages.parquet
```

但真实文件其实在：

```text
/Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset/MMDocIR_pages.parquet
```

项目里的这个路径只是一个指向真实文件的链接。

## 2. 为什么本项目使用软链接

因为 MMDocIR 数据很大：

```text
/Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset 约 10GB
```

如果复制到项目里，会变成：

```text
桌面一份 10GB
项目里一份 10GB
```

这样浪费磁盘空间。

使用软链接后：

```text
桌面保存真实数据
项目里保存入口
```

代码依然可以从项目路径读取数据，但不重复占空间。

## 3. 软链接和复制的区别

| 操作 | 是否产生新文件内容 | 是否额外占大空间 | 原文件移动后是否受影响 |
|---|---|---|---|
| 复制 | 是 | 是 | 不受影响 |
| 软链接 | 否 | 否 | 会受影响 |

所以软链接适合：

- 大数据集；
- 多个项目共用同一份数据；
- 不想重复占用磁盘；
- 希望项目目录保持标准数据入口。

不适合：

- 原始文件经常移动；
- 需要把项目完整打包发给别人；
- 目标机器上没有原始文件路径。

## 4. 软链接和硬链接的区别

常见链接有两种：

```text
软链接 symbolic link
硬链接 hard link
```

本项目使用的是软链接。

简单对比：

| 类型 | 特点 |
|---|---|
| 软链接 | 保存的是目标路径，像快捷方式 |
| 硬链接 | 指向同一个底层文件内容 |

软链接更直观，也能链接目录；硬链接通常不能直接链接目录，理解成本更高。

本项目只需要理解软链接即可。

## 5. 如何创建软链接

命令格式：

```bash
ln -s 真实文件路径 链接路径
```

例如：

```bash
ln -s /Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset/MMDocIR_pages.parquet data/raw/mmdocir/MMDocIR_pages.parquet
```

意思是：

```text
在 data/raw/mmdocir/ 下创建一个入口
这个入口指向桌面上的真实 parquet 文件
```

## 6. 本项目是如何创建软链接的

中文年报 PDF 是批量链接：

```bash
for f in /Users/zhouwenjing/Desktop/DataSets/*.pdf; do
  ln -sf "$f" "data/raw/cn_annual_reports/pdfs/$(basename "$f")"
done
```

含义：

1. 遍历桌面 `DataSets` 下所有 PDF。
2. 每个 PDF 都在项目的 `data/raw/cn_annual_reports/pdfs/` 下创建一个同名软链接。
3. `-s` 表示创建软链接。
4. `-f` 表示如果同名链接已存在，就覆盖。

MMDocIR 顶层文件和目录是这样链接的：

```bash
for f in /Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset/*; do
  ln -sfn "$f" "data/raw/mmdocir/$(basename "$f")"
done
```

含义：

1. 遍历 MMDocIR 顶层所有文件和文件夹。
2. 在项目 `data/raw/mmdocir/` 下创建同名软链接。
3. `-n` 用于处理目录链接时更安全。

## 7. 如何查看软链接

使用：

```bash
ls -la data/raw/mmdocir
```

软链接会显示成：

```text
MMDocIR_pages.parquet -> /Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset/MMDocIR_pages.parquet
```

箭头左边是项目里的链接路径，箭头右边是真实文件路径。

## 8. 如何只查看链接目标

使用：

```bash
readlink data/raw/mmdocir/MMDocIR_pages.parquet
```

输出类似：

```text
/Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset/MMDocIR_pages.parquet
```

也可以看目录链接：

```bash
readlink data/raw/mmdocir/doc_miscellaneous
```

## 9. 如何确认软链接是否可用

如果软链接可用，下面命令应该能看到文件：

```bash
ls -lh data/raw/mmdocir/MMDocIR_pages.parquet
```

如果目标不存在，可能会出现：

```text
No such file or directory
```

也可以用：

```bash
test -e data/raw/mmdocir/MMDocIR_pages.parquet && echo ok
```

输出 `ok` 表示可访问。

## 10. 如何查找项目里的软链接

查找中文年报软链接数量：

```bash
find data/raw/cn_annual_reports/pdfs -maxdepth 1 -type l | wc -l
```

查找 MMDocIR 顶层软链接数量：

```bash
find data/raw/mmdocir -maxdepth 1 -type l | wc -l
```

当前项目中：

```text
中文年报 PDF 软链接数量：20
MMDocIR 顶层软链接数量：5
```

## 11. 为什么 du 显示 0B

你可能会看到：

```bash
du -sh data/raw/mmdocir
```

输出：

```text
0B
```

这是正常的。

因为项目里的 `data/raw/mmdocir` 只保存软链接本身，不保存真实 10GB 数据。

真实数据占用仍在：

```text
/Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset
```

## 12. 软链接失效是什么情况

如果你把桌面原始数据移动了，比如从：

```text
/Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset
```

移动到：

```text
/Users/zhouwenjing/Documents/Data/MMDocIR_Evaluation_Dataset
```

项目里的软链接仍然指向旧路径，就会失效。

这时候需要重新创建软链接。

## 13. 如何删除软链接

删除软链接使用：

```bash
rm data/raw/mmdocir/MMDocIR_pages.parquet
```

注意：

- 删除软链接不会删除真实文件；
- 真实文件仍然在桌面。

如果删除的是目录软链接：

```bash
rm data/raw/mmdocir/doc_miscellaneous
```

不要在软链接目录后面加 `/`，避免误操作真实目录。

## 14. 如何重新创建软链接

如果链接失效，可以先删掉旧链接：

```bash
rm data/raw/mmdocir/MMDocIR_pages.parquet
```

再重新创建：

```bash
ln -s /Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset/MMDocIR_pages.parquet data/raw/mmdocir/MMDocIR_pages.parquet
```

如果要批量重建 MMDocIR 顶层链接：

```bash
for f in /Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset/*; do
  ln -sfn "$f" "data/raw/mmdocir/$(basename "$f")"
done
```

## 15. Git 会怎么处理软链接

Git 可以记录软链接本身。

但是本项目的 `.gitignore` 忽略了：

```text
data/raw/
data/interim/
data/processed/
artifacts/
runs/
```

所以这些数据链接不会被提交到 Git。

这是有意设计的，因为数据集很大，不应该提交到代码仓库。

## 16. 代码如何使用软链接

代码不需要知道这是软链接。

例如：

```python
import polars as pl

df = pl.scan_parquet("data/raw/mmdocir/MMDocIR_pages.parquet")
```

Python 会像读取普通文件一样读取它。

文件系统会自动把访问转到真实路径：

```text
/Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset/MMDocIR_pages.parquet
```

## 17. 本项目当前软链接结构

当前中文年报：

```text
data/raw/cn_annual_reports/pdfs/*.pdf
```

指向：

```text
/Users/zhouwenjing/Desktop/DataSets/*.pdf
```

当前 MMDocIR：

```text
data/raw/mmdocir/MMDocIR_annotations.jsonl
data/raw/mmdocir/MMDocIR_pages.parquet
data/raw/mmdocir/MMDocIR_layouts.parquet
data/raw/mmdocir/README.md
data/raw/mmdocir/doc_miscellaneous
```

指向：

```text
/Users/zhouwenjing/Desktop/MMDocIR_Evaluation_Dataset/...
```

## 18. 常见问题

### 18.1 软链接是不是复制文件

不是。它只是保存一个目标路径。

### 18.2 软链接会不会占用 10GB

不会。它本身很小，通常只有几十字节到几百字节。

### 18.3 删除软链接会不会删除真实数据

正常删除软链接不会删除真实数据。

### 18.4 真实数据移动后怎么办

重新创建软链接。

### 18.5 代码能不能直接读取软链接

可以。大多数程序都会把软链接当成普通文件路径处理。

## 19. 当前阶段你最需要掌握的命令

查看软链接：

```bash
ls -la data/raw/mmdocir
```

查看真实目标：

```bash
readlink data/raw/mmdocir/MMDocIR_pages.parquet
```

确认链接可访问：

```bash
test -e data/raw/mmdocir/MMDocIR_pages.parquet && echo ok
```

统计软链接数量：

```bash
find data/raw/mmdocir -maxdepth 1 -type l | wc -l
```

重新创建软链接：

```bash
ln -sfn /真实路径 /项目中的链接路径
```

理解这些，就能清楚为什么项目目录里看到了数据，但磁盘空间没有增加。

