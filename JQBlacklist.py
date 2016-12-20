'''
Created on Dec 9, 2016

@Author: Cyanife
'''
import tkinter as tk
from tkinter import filedialog
import tkinter.ttk as ttk
import tkinter.font as tkfont

import json
import re

import webbrowser
import asyncio
import aiohttp
import yarl

class StockDuplicateException(Exception):
    def __init__(self, stock):
        Exception.__init__(self)
        self.stock = stock

class StockEmptyException(Exception):
    def __init__(self, stock):
        Exception.__init__(self)
        self.stock = stock

class BlacklistData(object):
    '''
    read blacklist.py and edit
    '''
    grep_detail = re.compile(r'(\w{2}\d+)=([^\s][^,]+?)%s%s' % (r',([\.\d]+)' * 29, r',([-\.\d:]+)' * 2))
    stock_api = 'http://hq.sinajs.cn/?format=text&list='

    def __init__(self):
        self._stocklist = []
        self._stockdict = {}
        self._path = ''
        self._haschanged = False
    
    def load(self, path):
        self._path = path
        with open(path,'r') as f:
            stocklist = json.load(f)
        #Convert symbol format
        self._stocklist = []
        for sym in stocklist:
            sym = re.sub(r'(\d+).XSHG', 'sh\g<1>', sym)
            sym = re.sub(r'(\d+).XSHE', 'sz\g<1>', sym)
            self._stocklist.append(sym)
        self.updatestockdict()

    def save(self):
        #update stocklist from stockdict
        self.updatestocklist()
        #Convert symbol format to JQ
        stocklist = []
        for sym in self._stocklist:
            sym = re.sub(r'sh(\d+)', '\g<1>.XSHG', sym)
            sym = re.sub(r'sz(\d+)', '\g<1>.XSHE', sym)
            stocklist.append(sym)
        #write json
        with open(self._path,'w') as f:
            json.dump(stocklist,f)

    @property 
    def stockdict(self):
        return self._stockdict
    
    def appendstock(self, symbol):
        if symbol in self._stockdict:
            raise StockDuplicateException(symbol)
        else:
            self._stockdict.update(self.getstockinfo([symbol]))
            self.updatestocklist()

    def removestock(self,symbol):
        if symbol not in self._stockdict:
            raise StockEmptyException(symbol)
        else:
            del self._stockdict[symbol]
            self.updatestocklist()
    
    def updatestocklist(self):
        self._stocklist = list(self._stockdict.keys())

    def updatestockdict(self):
        self._stockdict = self.getstockinfo(self._stocklist)

    def getstockinfo(self,stocklist):
        self._session = aiohttp.ClientSession()
        coroutines = []
        for symbol in stocklist:
            coroutine = self.gatherstockinfo(symbol)
            coroutines.append(coroutine)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        res = loop.run_until_complete(asyncio.gather(*coroutines))

        self._session.close()
        return self.stockinfoformatter(res)

    async def gatherstockinfo(self,symbol):
        headers = {
            'Accept-Encoding': 'gzip, deflate, sdch',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.100 Safari/537.36'
        }
        url = yarl.URL(self.stock_api + symbol, encoded=True)
        try:
            async with self._session.get(url, timeout=10, headers=headers) as r:
                response_text = await r.text()
                return response_text
        except asyncio.TimeoutError:
            return None
    
    def stockinfoformatter(self,rep_data):
        stocks_detail = ''.join(rep_data)
        grep_str = self.grep_detail
        result = grep_str.finditer(stocks_detail)
        stock_dict = dict()
        for stock_match_object in result:
            stock = stock_match_object.groups()
            stock_dict[stock[0]] = dict(
                name=stock[1],
                open=float(stock[2]),
                close=float(stock[3]),
                now=float(stock[4]),
                high=float(stock[5]),
                low=float(stock[6]),
                buy=float(stock[7]),
                sell=float(stock[8]),
                turnover=int(stock[9]),
                volume=float(stock[10]),
                bid1_volume=int(stock[11]),
                bid1=float(stock[12]),
                bid2_volume=int(stock[13]),
                bid2=float(stock[14]),
                bid3_volume=int(stock[15]),
                bid3=float(stock[16]),
                bid4_volume=int(stock[17]),
                bid4=float(stock[18]),
                bid5_volume=int(stock[19]),
                bid5=float(stock[20]),
                ask1_volume=int(stock[21]),
                ask1=float(stock[22]),
                ask2_volume=int(stock[23]),
                ask2=float(stock[24]),
                ask3_volume=int(stock[25]),
                ask3=float(stock[26]),
                ask4_volume=int(stock[27]),
                ask4=float(stock[28]),
                ask5_volume=int(stock[29]),
                ask5=float(stock[30]),
                date=stock[31],
                time=stock[32],
            )
        return stock_dict

class BlacklistEditor(tk.Frame):
    '''
    GUI
    '''
    xqURL = 'https://xueqiu.com/S/' 


    def __init__(self, parent):
        '''
        Constructor
        '''
        #Inner settings
        self._header = ['name','price']
        self._filepath = 'blacklist.json'

        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.initialize_user_interface()
        self._haschanged = False 

    def initialize_user_interface(self):
        '''
        Use treeview
        '''
        self.parent.title("JQBlacklist")
        self.parent.grid_rowconfigure(2,weight=1)#窗口缩放时行列权重
        self.parent.grid_columnconfigure(0,weight=1)
        self.parent.config(background="lavender")

        #Set GUI widgets
        self.load_button = tk.Button(self.parent, text = 'Open',width = 10, command = self.load_blacklist)
        self.load_button.grid(row = 0, column = 0, sticky = tk.W)
        self.save_button = tk.Button(self.parent, text = 'Save', width = 10, command = self.save_blacklist)
        self.save_button.grid(row = 1, column = 0, sticky = tk.W)
        self.insert_button = tk.Button(self.parent, text = 'Insert', width = 10, command = self.insert_stock)
        self.insert_button.grid(row = 0, column = 1, sticky = tk.W)
        self.delete_button = tk.Button(self.parent, text = 'Delete', width = 10, command = self.delete_stock)
        self.delete_button.grid(row = 0, column = 2, sticky = tk.E)
        
        self.stock_entry = tk.Entry(self.parent,width = 25)
        self.stock_entry.grid(row = 1, column=1,columnspan=2)
        
        #Set the treeview
        # self.tree = ttk.Treeview(self.parent, columns=self._header,show="headings")
        self.tree = ttk.Treeview(self.parent, columns=self._header)

        self.vsb = ttk.Scrollbar(orient="vertical",
            command=self.tree.yview)
        self.hsb = ttk.Scrollbar(orient="horizontal",
            command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vsb.set,
            xscrollcommand=self.hsb.set)
        self.tree.grid(row = 2, columnspan = 3, sticky = 'nsew')
        self.vsb.grid(column=3, row=2, sticky='ns') 
        self.hsb.grid(column=0, row=3,columnspan=3,sticky='ew')

        #bind treeview events
        self.tree.bind("<<TreeviewSelect>>", self.stockclick)
        self.tree.bind("<Double-1>", self.OnDoubleClick)
    
    def OnDoubleClick(self, event):
        item = self.tree.identify('item', event.x,event.y)
        symbol = self.tree.item(item,'text')
        webbrowser.open(self.xqURL+symbol, new=2)

    def stockclick(self, event):
        currentitems = self.tree.selection()
        # print(type(currentitems))
        self.stock_entry.delete(0,'end')
        if len(currentitems) == 1:
            self.stock_entry.insert('end', self.tree.item(currentitems[0], 'text'))

    def load_blacklist(self):
        ftypes = [('Blacklist files', '*.json'), ('All files', '*')]
        opendlg = filedialog.Open(self, filetypes = ftypes)
        fload = opendlg.show() 

        if fload != '':
            self._filepath = fload
            self._blacklistdata = BlacklistData()
            self._blacklistdata.load(self._filepath)
            # print(self._blacklistdata.stockdict)
            self._build_tree()
    
    def _build_tree(self):
        self.tree.heading('#0', text = 'symbol', command = lambda:self.sortsymbol(self.tree,0))
        self.tree.column('#0', stretch=tk.YES)
        for col in self._header:
            self.tree.heading(col, text = col.title(), command = lambda c=col: self.sortby(self.tree,c,0))
            #adjust the column's width
            # self.tree.column(col, width=tkfont.Font().measure(col.title()))
        
        for symbol, info in self._blacklistdata.stockdict.items():
            item = (info['name'],info['now'])
            self.tree.insert('','end',text=symbol,values= item)
            # adjust column's width
            # for ix, val in enumerate(item):
            #     col_w = tkfont.Font().measure(val)
            #     if self.tree.column(self._header[ix],width = None) <col_w:
            #         self.tree.column(self._header[ix], width = col_w)

    def sortby(self, tree, col, descending):
        """sort tree contents when a column header is clicked on"""
        # grab values to sort
        data = [(tree.set(child, col), child) for child in tree.get_children('')]
        # now sort the data in place
        data.sort(reverse=descending)
        for ix, item in enumerate(data):
            tree.move(item[1], '', ix)
        # switch the heading so it will sort in the opposite direction
        tree.heading(col, command=lambda col=col: self.sortby(tree, col, int(not descending)))

    def sortsymbol(self, tree, descending):
        """sort tree contents when a column header is clicked on"""
        # grab values to sort
        data = [(tree.item(child, 'text')[2:], child) for child in tree.get_children()]
        # now sort the data in place
        data.sort(reverse=descending)
        for ix, item in enumerate(data):
            tree.move(item[1], '', ix)
        # switch the heading so it will sort in the opposite direction
        tree.heading('#0', command = lambda: self.sortsymbol(tree, int(not descending)))
    
    def save_blacklist(self):
        if self._haschanged:
            self._blacklistdata.save()
            self._haschanged = False
    
    def insert_stock(self):
        symbol = self.stock_entry.get()
        try:
            self._blacklistdata.appendstock(symbol)
            info = self._blacklistdata.stockdict[symbol]
            item = (info['name'],info['now'])
            self.tree.insert('','end',text=symbol,values= item)
        except StockDuplicateException:
            pass

        self._haschanged = True
        
    def delete_stock(self):
        symbol = self.stock_entry.get()
        if symbol:
            try:
                children = self.tree.get_children()
                for chd in children:
                    if self.tree.item(chd,'text') == symbol:
                        self.tree.delete(chd)
                self._blacklistdata.removestock(symbol)
            except StockEmptyException:
                pass
        else:
            currentitems = self.tree.selection()
            for item in currentitems:
                try:
                    symbol = self.tree.item(item, 'text')
                    self.tree.delete(item)
                    self._blacklistdata.removestock(symbol)
                except StockEmptyException:
                    pass

        self._haschanged = True

def main():
    root=tk.Tk()
    Editor=BlacklistEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()