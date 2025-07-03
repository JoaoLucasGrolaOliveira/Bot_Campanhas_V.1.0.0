import os
import threading
import sqlite3
import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

DB_FILE = 'campaigns.db'
DEFAULT_CHANNELS = [
    'Amazon Global Api', 'B2W Nova API', 'Magazine Luiza', 'Via Varejo',
    'Leroy Merlin', 'Madeira Madeira', 'Lojas Colombo Nova API', 'MOBLY',
    'BRADESCO SHOP', 'Carrefour', 'BUSCAPÉ', 'Shopee', 'Mercado livre'
]

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            marketplace TEXT,
            sku TEXT,
            produto TEXT,
            preco REAL,
            desconto1 REAL,
            desconto2 REAL,
            start_date TEXT,
            end_date TEXT
        )
    ''')
    conn.commit()
    conn.close()


def save_campaigns_df(df: pd.DataFrame):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    df.to_sql('campaigns', conn, if_exists='replace', index=False)
    conn.close()


def load_campaign_db() -> pd.DataFrame:
    init_db()
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql('SELECT * FROM campaigns', conn)
    conn.close()
    return df

def gerar_justificativa_preco(preco_venda, precos_validos):
    return f"Preço vendido R${preco_venda:.2f}. Valores válidos: " + ", ".join([f'R${p:.2f}' for p in precos_validos])

def gerar_justificativa_desconto(desconto_venda, descontos_validos):
    return f"Desconto aplicado {desconto_venda:.2f}%. Permitidos: " + ", ".join([f'{d:.2f}%' for d in descontos_validos])

def validar_linha(row, camp_df):
    sku = row['SKU']
    mp = row['MARKETPLACE'].strip().lower()
    pv = float(row['VALOR_TOTAL'])
    if 'mercadolivre' in mp or 'shopee' in mp:
        return 'Ignorado', 'Marketplace não analisado', 0.0
    subset = camp_df[(camp_df['sku']==sku) & (camp_df['marketplace']==mp)]
    if subset.empty:
        return 'Erro grave', 'SKU/Marketplace não encontrado', 100.0
    pb = float(subset['preco'].iloc[0])
    d1 = float(subset['desconto1'].iloc[0])
    d2 = float(subset['desconto2'].iloc[0])
    if pb == 0:
        return 'Erro grave', 'Preço base é zero', 100.0
    if round(pv,2) == round(pb,2):
        return 'Correto', 'Preço exato', 0.0
    desc = (1 - pv/pb)*100
    maxd = max(d1, d2)
    if desc <= maxd:
        return 'Correto', f'Desconto {desc:.2f}% ≤ máximo {maxd:.2f}%', 0.0
    err = abs(pv-pb)/pb*100
    return 'Incorreto', f'Vendido R${pv:.2f}, esperado R${pb:.2f}', round(err,2)

class ValidadorApp:
    def __init__(self, master):
        self.master = master
        master.title("Validador de Planilhas - Adonai Estofados")
        master.geometry('900x650')
        try:
            self.bg_image = tk.PhotoImage(file='adonai_bg.png')
            tk.Label(master, image=self.bg_image).place(x=0, y=0, relwidth=1, relheight=1)
        except:
            pass
        self.cancel_flag = False
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TButton', background='#FFA500', foreground='white')
        style.map('TButton', background=[('active','#FF8C00')])
        style.configure('TLabel', background='white')
        style.configure('TNotebook', background='white')
        notebook = ttk.Notebook(master)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        self.tab_campaign = ttk.Frame(notebook)
        self.tab_validation = ttk.Frame(notebook)
        notebook.add(self.tab_campaign, text='Campanhas (mensal)')
        notebook.add(self.tab_validation, text='Validação (diário)')
        self.build_campaign_tab()
        self.build_validation_tab()
        ttk.Label(master, text="By João Lucas - Adonai Estofados", background='white').pack(side='bottom', pady=5)

    def build_campaign_tab(self):
        f = self.tab_campaign
        ttk.Label(f, text='Canal:').grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.cmb_channel = ttk.Combobox(f, state='readonly')
        self.cmb_channel.grid(row=0, column=1, sticky='w')
        self.cmb_channel['values'] = ['Todos'] + sorted(set(DEFAULT_CHANNELS) | set(load_campaign_db()['marketplace']))
        self.cmb_channel.set('Todos')
        self.cmb_channel.bind('<<ComboboxSelected>>', lambda e: self.reload_channels())
        ttk.Button(f, text='Recarregar', command=self.reload_channels).grid(row=0, column=2)
        ttk.Button(f, text='Excluir Canal', command=self.delete_channel).grid(row=0, column=3)
        cols = ['SKU','Produto','Preço','Desconto1','Desconto2','Start','End']
        self.tree_campaign = ttk.Treeview(f, columns=cols, show='headings')
        for c in cols:
            self.tree_campaign.heading(c, text=c)
            self.tree_campaign.column(c, width=100)
        self.tree_campaign.grid(row=1, column=0, columnspan=4, pady=10)
        self.tree_campaign.bind('<Double-1>', self.edit_cell)
        ttk.Button(f, text='Add Linha', command=self.add_row).grid(row=2, column=0)
        ttk.Button(f, text='Del Linha', command=self.del_row).grid(row=2, column=1)
        ttk.Button(f, text='Salvar', command=self.save_campaigns).grid(row=2, column=2)
        ttk.Button(f, text='Excluir Sel', command=self.delete_and_save_campaign).grid(row=2, column=3)
        self.reload_channels()

    def reload_channels(self):
        df = load_campaign_db()
        db_chans = set(df['marketplace'])
        channels = sorted(set(DEFAULT_CHANNELS) | db_chans)
        self.cmb_channel['values'] = ['Todos'] + channels
        current = self.cmb_channel.get()
        if current not in channels:
            self.cmb_channel.set('Todos')
        for iid in self.tree_campaign.get_children():
            self.tree_campaign.delete(iid)
        if self.cmb_channel.get() != 'Todos':
            for _, r in df[df['marketplace']==self.cmb_channel.get()].iterrows():
                self.tree_campaign.insert('', 'end', values=(r['sku'],r['produto'],r['preco'],r['desconto1'],r['desconto2'],r['start_date'],r['end_date']))

    def delete_channel(self):
        chan = self.cmb_channel.get()
        if chan == 'Todos':
            messagebox.showwarning('Atenção','Selecione um canal')
            return
        if not messagebox.askyesno('Confirmar', f'Excluir campanhas de {chan}?'):
            return
        df = load_campaign_db()
        save_campaigns_df(df[df['marketplace'] != chan])
        messagebox.showinfo('Sucesso', f'Campanhas de {chan} excluídas.')
        self.reload_channels()

    def add_row(self):
        self.tree_campaign.insert('', 'end', values=('','','0.0','0.0','0.0','',''))

    def del_row(self):
        for iid in self.tree_campaign.selection():
            self.tree_campaign.delete(iid)

    def delete_and_save_campaign(self):
        sels = self.tree_campaign.selection()
        if not sels:
            messagebox.showwarning('Atenção','Selecione linhas')
            return
        if not messagebox.askyesno('Confirmar','Excluir linhas selecionadas?'):
            return
        for iid in sels:
            self.tree_campaign.delete(iid)
        self.save_campaigns()

    def save_campaigns(self):
        chan = self.cmb_channel.get()
        if chan == 'Todos':
            messagebox.showwarning('Atenção','Selecione um canal')
            return
        rows = []
        for iid in self.tree_campaign.get_children():
            sku, prod, pre, d1, d2, sd, ed = self.tree_campaign.item(iid)['values']
            try:
                pre = float(pre); d1 = float(d1); d2 = float(d2)
            except:
                messagebox.showerror('Erro','Valores inválidos')
                return
            rows.append({'marketplace':chan,'sku':sku.strip().upper(),'produto':prod,'preco':pre,'desconto1':d1,'desconto2':d2,'start_date':sd,'end_date':ed})
        df_old = load_campaign_db()
        save_campaigns_df(pd.concat([df_old[df_old['marketplace']!=chan], pd.DataFrame(rows)], ignore_index=True))
        messagebox.showinfo('Sucesso','Campanhas salvas')

    def edit_cell(self, event):
        tr = self.tree_campaign
        row = tr.identify_row(event.y); col = tr.identify_column(event.x)
        if not row or not col: return
        x,y,w,h = tr.bbox(row,col)
        ci = int(col.replace('#',''))-1; cn=tr['columns'][ci]
        val = tr.set(row,cn)
        ent = tk.Entry(tr); ent.place(x=x,y=y,width=w,height=h); ent.insert(0,val); ent.focus()
        def on_c(e): tr.set(row,cn,ent.get()); ent.destroy()
        ent.bind('<FocusOut>',on_c); ent.bind('<Return>',on_c)

    def build_validation_tab(self):
        f = self.tab_validation
        ttk.Label(f, text='Filtrar por Canal:').grid(row=0,column=0,padx=5,pady=5,sticky='e')
        self.cmb_valchan = ttk.Combobox(f, state='readonly')
        self.cmb_valchan.grid(row=0,column=1,sticky='w')
        self.reload_val_channels()
        ttk.Button(f, text='Recarregar', command=self.reload_val_channels).grid(row=0,column=2)
        ttk.Button(f, text='Selecionar Planilha de Vendas', command=self.select_sales_file).grid(row=1,column=0,pady=5)
        self.lbl_sales = ttk.Label(f, text='Nenhum arquivo selecionado')
        self.lbl_sales.grid(row=1,column=1,columnspan=2,sticky='w')
        self.progress = ttk.Progressbar(f, orient='horizontal', length=600, mode='determinate')
        self.progress.grid(row=2,column=0,columnspan=3,pady=10)
        btnf = ttk.Frame(f); btnf.grid(row=3,column=0,columnspan=3)
        ttk.Button(btnf, text='Iniciar Validação', command=self.start_validation).grid(row=0,column=0,padx=5)
        ttk.Button(btnf, text='Cancelar', command=self.cancel_validation).grid(row=0,column=1,padx=5)
        self.status_label = ttk.Label(f, text='', background='white')
        self.status_label.grid(row=4,column=0,columnspan=3,pady=5)

    def reload_val_channels(self):
        df = load_campaign_db()
        chans = sorted(set(DEFAULT_CHANNELS) | set(df['marketplace']))
        self.cmb_valchan['values'] = ['Todos'] + chans
        self.cmb_valchan.set('Todos')

    def select_sales_file(self):
        path = filedialog.askopenfilename(title='Selecione a planilha de VENDAS', filetypes=[('Excel','*.xlsx *.xls')])
        if path:
            self.sales_path = path
            self.lbl_sales.config(text=os.path.basename(path))

    def cancel_validation(self):
        self.cancel_flag = True
        self.status_label.config(text='Validação cancelada!')

    def start_validation(self):
        if not hasattr(self,'sales_path'):
            messagebox.showwarning('Atenção','Selecione planilha de vendas')
            return
        save_path = filedialog.asksaveasfilename(defaultextension='.xlsx', filetypes=[('Excel','*.xlsx')])
        if not save_path:
            return
        self.cancel_flag=False
        threading.Thread(target=self.validate,args=(self.sales_path,save_path),daemon=True).start()

    def validate(self,sales_path,save_path):
        camp_df = load_campaign_db()
        try:
            sales=pd.read_excel(sales_path,usecols=[8,22,25,28],dtype=str)
            sales.columns=['MARKETPLACE','VALOR_TOTAL','TITULO','SKU']
            sales['MARKETPLACE']=sales['MARKETPLACE'].str.strip().str.lower()
            sales['SKU']=sales['SKU'].str.strip().str.upper()
        except Exception as e:
            messagebox.showerror('Erro',f'Falha ao ler vendas:{e}')
            return
        chan=self.cmb_valchan.get(); n=len(sales); results=[]
        for i,row in enumerate(sales.itertuples(index=False),start=1):
            if self.cancel_flag: break
            self.progress['value']=i/n*100; self.status_label.config(text=f'Processando {i}/{n}...')
            mp=row.MARKETPLACE
            if chan!='Todos' and mp!=chan:
                st,js,er='Ignorado','Canal diferente',0.0
            else:
                st,js,er=validar_linha({'SKU':row.SKU,'MARKETPLACE':mp,'VALOR_TOTAL':row.VALOR_TOTAL},camp_df)
            results.append({'MARKETPLACE':mp,'VALOR_TOTAL':row.VALOR_TOTAL,'TITULO':row.TITULO,'SKU':row.SKU,'Status':st,'Justificativa':js,'Erro (%)':er})
        if self.cancel_flag:
            self.progress['value']=0
            return
        df_out=pd.DataFrame(results)
        try:
            with pd.ExcelWriter(save_path,engine='xlsxwriter') as w:
                df_out.to_excel(w,index=False)
                wb,ws=w.book,w.sheets['Sheet1']
                fmt_g=wb.add_format({'bg_color':'#C6EFCE'})
                fmt_r=wb.add_format({'bg_color':'#FFC7CE'})
                for idx,s in enumerate(df_out['Status'],start=1):
                    ws.set_row(idx,None,fmt_g if s=='Correto' else fmt_r)
        except:
            df_out.to_excel(save_path,index=False)
        self.progress['value']=100
        self.status_label.config(text='Validação concluída!')

if __name__=='__main__':
    init_db()
    root=tk.Tk()
    app=ValidadorApp(root)
    root.mainloop()
