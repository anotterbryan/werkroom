import re
def _sp(v):
    try: return max(1,int(v))
    except: return 1
def table_to_grid(table, sep=''):
    """HTML table -> matrix honoring colspan & rowspan (robust to junk span values)."""
    trs=table.find_all('tr'); occ={}; nrow=len(trs); maxc=0
    for r,tr in enumerate(trs):
        c=0
        for cell in tr.find_all(['td','th']):
            while (r,c) in occ: c+=1
            txt=re.sub(r'\s+',' ',cell.get_text(sep,strip=True)).strip()
            cs=_sp(cell.get('colspan',1)); rs=_sp(cell.get('rowspan',1))
            for dr in range(rs):
                for dc in range(cs):
                    occ[(r+dr,c+dc)]=txt
            c+=cs; maxc=max(maxc,c)
    return [[occ.get((r,c),'') for c in range(maxc)] for r in range(nrow)]
