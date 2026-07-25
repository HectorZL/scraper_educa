import openpyxl
libro = openpyxl.load_workbook('sb2.xlsx', read_only=True)
for i, hoja in enumerate(libro.sheetnames, 1):
    print(f"{i}. {hoja}")
