#!/usr/bin/env python3
"""
Parempi QR-generaattori – reaaliaikainen GUI + WiFi + logo + tiedosto base64
"""

import os
import base64
from typing import Optional, Tuple
import segno
from PIL import Image, ImageDraw, ImageTk
import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox, ttk

# -------------------------
# QR GENEROINTI
# -------------------------
def _ensure_dir_for_file(path: str):
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

def parse_color(s: str) -> Tuple[int,int,int]:
    s = s.strip()
    if s.startswith("#"): s = s[1:]
    if len(s)!=6: raise ValueError("Väri 6-merkkinen heksadesimaali, esim. #1a2b3c")
    return (int(s[0:2],16), int(s[2:4],16), int(s[4:6],16))

def create_qr(text: str, out: Optional[str]=None, kind: str="png",
              scale:int=10,module_size:int=10,border:int=4,
              error:str='M',dark:str="#000000",light:str="#FFFFFF",
              rounded:bool=False, logo:Optional[str]=None, logo_scale:float=0.2):
    qr = segno.make(text,error=error)
    ext = ".png" if not out else os.path.splitext(out)[1].lower()
    if ext==".svg" or kind.lower()=="svg":
        if out: _ensure_dir_for_file(out); qr.save(out,kind="svg",scale=scale,dark=dark,light=light,border=border); return out
        else: return qr

    rgb_dark = parse_color(dark)
    rgb_light = parse_color(light)
    matrix = list(qr.matrix)
    size = len(matrix)+2*border
    px = size*module_size
    img = Image.new("RGB",(px,px),rgb_light)
    draw = ImageDraw.Draw(img)

    for r,row in enumerate(matrix):
        for c,val in enumerate(row):
            if not val: continue
            x1=(c+border)*module_size
            y1=(r+border)*module_size
            x2=x1+module_size
            y2=y1+module_size
            if rounded:
                pad=module_size*0.1
                draw.ellipse([x1+pad,y1+pad,x2-pad,y2-pad],fill=rgb_dark)
            else:
                draw.rectangle([x1,y1,x2,y2],fill=rgb_dark)

    if logo:
        logo_img=Image.open(logo).convert("RGBA")
        bw,bh=img.size
        max_logo=int(min(bw,bh)*logo_scale)
        logo_img.thumbnail((max_logo,max_logo),Image.Resampling.LANCZOS)
        lx=(bw-logo_img.width)//2
        ly=(bh-logo_img.height)//2
        padding=int(min(logo_img.width,logo_img.height)*0.18)
        bg=Image.new("RGBA",(logo_img.width+2*padding,logo_img.height+2*padding),(255,255,255,255))
        mask=Image.new("L",bg.size,0)
        ImageDraw.Draw(mask).rounded_rectangle([0,0,*bg.size],radius=padding+4,fill=255)
        img=img.convert("RGBA")
        img.paste(bg,(lx-padding,ly-padding),mask)
        img.paste(logo_img,(lx,ly),logo_img)
        img=img.convert("RGB")

    if out:
        _ensure_dir_for_file(out)
        fmt = "PNG"
        if ext==".jpg" or ext==".jpeg": fmt="JPEG"
        elif ext==".bmp": fmt="BMP"
        img.save(out,fmt)
        return out
    else:
        return img

# -------------------------
# GUI
# -------------------------
class QRGeneratorGUI:
    def __init__(self,root):
        self.root=root
        self.root.title("Parempi QR-generaattori")
        self.logo_path=None
        self.style=ttk.Style(root)
        self.style.theme_use("clam")

        mainframe=ttk.Frame(root,padding="10")
        mainframe.grid(row=0,column=0,sticky="NSEW")
        root.columnconfigure(0,weight=1)
        root.rowconfigure(0,weight=1)

        # Sisältö
        ttk.Label(mainframe,text="Sisältö:").grid(row=0,column=0,sticky="e")
        self.content_entry=ttk.Entry(mainframe,width=50)
        self.content_entry.grid(row=0,column=1,columnspan=3,padx=5,pady=5)
        self.content_entry.bind("<KeyRelease>", lambda e: self.update_preview())
        ttk.Button(mainframe,text="Lataa tiedosto...",command=self.load_file_content).grid(row=0,column=4,padx=5)

        # Tiedosto
        ttk.Label(mainframe,text="Tiedosto:").grid(row=1,column=0,sticky="e")
        self.out_entry=ttk.Entry(mainframe,width=50)
        self.out_entry.grid(row=1,column=1,columnspan=2,padx=5,pady=5)
        ttk.Button(mainframe,text="Valitse...",command=self.choose_file).grid(row=1,column=3)

        # Formaatti
        ttk.Label(mainframe,text="Formaatti:").grid(row=2,column=0,sticky="e")
        self.format_var=tk.StringVar(value="png")
        ttk.OptionMenu(mainframe,self.format_var,"png","png","jpg","bmp","svg").grid(row=2,column=1,sticky="w")

        # Värit
        ttk.Label(mainframe,text="Etuväri:").grid(row=3,column=0,sticky="e")
        self.fg_color_btn=ttk.Button(mainframe,text="#000000",command=self.choose_fg)
        self.fg_color_btn.grid(row=3,column=1,sticky="w")
        self.fg_color_btn.bind("<ButtonRelease-1>", lambda e: self.update_preview())

        ttk.Label(mainframe,text="Taustaväri:").grid(row=3,column=2,sticky="e")
        self.bg_color_btn=ttk.Button(mainframe,text="#FFFFFF",command=self.choose_bg)
        self.bg_color_btn.grid(row=3,column=3,sticky="w")
        self.bg_color_btn.bind("<ButtonRelease-1>", lambda e: self.update_preview())

        # Pyöreät moduulit
        self.rounded_var=tk.BooleanVar()
        cb=ttk.Checkbutton(mainframe,text="Pyöreät moduulit",variable=self.rounded_var, command=self.update_preview)
        cb.grid(row=4,column=0,columnspan=2,sticky="w")

        # Logo
        ttk.Label(mainframe,text="Logo (valinnainen):").grid(row=5,column=0,sticky="e")
        ttk.Button(mainframe,text="Valitse logo...",command=self.choose_logo).grid(row=5,column=1,sticky="w")

        # WiFi-osio
        wifi_frame=ttk.LabelFrame(mainframe,text="WiFi QR",padding="5")
        wifi_frame.grid(row=6,column=0,columnspan=4,sticky="EW",pady=5)
        ttk.Label(wifi_frame,text="SSID:").grid(row=0,column=0,sticky="e")
        self.ssid_entry=ttk.Entry(wifi_frame,width=20)
        self.ssid_entry.grid(row=0,column=1,padx=5,pady=2)
        self.ssid_entry.bind("<KeyRelease>", lambda e: self.update_preview())
        ttk.Label(wifi_frame,text="Salasana:").grid(row=1,column=0,sticky="e")
        self.pass_entry=ttk.Entry(wifi_frame,width=20,show="*")
        self.pass_entry.grid(row=1,column=1,padx=5,pady=2)
        self.pass_entry.bind("<KeyRelease>", lambda e: self.update_preview())
        ttk.Label(wifi_frame,text="Tyyppi:").grid(row=2,column=0,sticky="e")
        self.security_var=tk.StringVar(value="WPA")
        om=ttk.OptionMenu(wifi_frame,self.security_var,"WPA","WPA","WEP","nopass", command=lambda e=None: self.update_preview())
        om.grid(row=2,column=1,sticky="w")

        # Generoi nappi
        ttk.Button(mainframe,text="Tallenna QR",command=self.save_qr).grid(row=7,column=0,columnspan=4,pady=10)

        # Esikatselu
        self.preview_label=ttk.Label(mainframe,text="QR esikatselu")
        self.preview_label.grid(row=8,column=0,columnspan=4)
        self.tk_preview=None

        # Päivitä aluksi
        self.update_preview()

    # -------------------------
    # Valinnat
    # -------------------------
    def choose_file(self):
        f=filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG","*.png"),("JPG","*.jpg"),("BMP","*.bmp"),("SVG","*.svg")])
        if f:
            self.out_entry.delete(0,tk.END)
            self.out_entry.insert(0,f)

    def choose_fg(self):
        color=colorchooser.askcolor()[1]
        if color: self.fg_color_btn.config(text=color)

    def choose_bg(self):
        color=colorchooser.askcolor()[1]
        if color: self.bg_color_btn.config(text=color)

    def choose_logo(self):
        f=filedialog.askopenfilename(filetypes=[("Kuvat","*.png;*.jpg;*.jpeg;*.bmp;*.gif")])
        if f: self.logo_path=f

    # -------------------------
    # Lataa tiedosto base64 sisällöksi
    # -------------------------
    def load_file_content(self):
        f = filedialog.askopenfilename(
            title="Valitse tiedosto",
            filetypes=[("Kaikki tiedostot","*.*")]
        )
        if f:
            try:
                with open(f, "rb") as file:
                    data = file.read()
                # Muutetaan base64-muotoon
                b64_data = base64.b64encode(data).decode('utf-8')
                self.content_entry.delete(0, tk.END)
                self.content_entry.insert(0, b64_data)
                self.update_preview()
                preview_text = b64_data[:200] + ("..." if len(b64_data)>200 else "")
                messagebox.showinfo("Tiedosto luettu", f"Tiedosto muunnettu base64:ksi (esikatselu: {preview_text})")
            except Exception as e:
                messagebox.showerror("Virhe", f"Tiedoston lukeminen epäonnistui:\n{e}")

    # -------------------------
    # Reaaliaikainen esikatselu
    # -------------------------
    def update_preview(self):
        ssid=self.ssid_entry.get().strip()
        password=self.pass_entry.get().strip()
        sec=self.security_var.get()
        content=self.content_entry.get().strip()
        if ssid: content=f"WIFI:S:{ssid};T:{sec};P:{password};;"
        elif not content: content=" "

        try:
            img=create_qr(
                text=content,
                dark=self.fg_color_btn['text'],
                light=self.bg_color_btn['text'],
                rounded=self.rounded_var.get(),
                logo=self.logo_path
            )
            img.thumbnail((300,300))
            self.tk_preview=ImageTk.PhotoImage(img)
            self.preview_label.config(image=self.tk_preview,text="")
        except:
            pass

    # -------------------------
    # Tallenna QR
    # -------------------------
    def save_qr(self):
        out=self.out_entry.get().strip()
        if not out:
            out=filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG","*.png"),("JPG","*.jpg"),("BMP","*.bmp"),("SVG","*.svg")])
            if not out: return
            self.out_entry.delete(0,tk.END)
            self.out_entry.insert(0,out)

        ssid=self.ssid_entry.get().strip()
        password=self.pass_entry.get().strip()
        sec=self.security_var.get()
        content=self.content_entry.get().strip()
        if ssid: content=f"WIFI:S:{ssid};T:{sec};P:{password};;"
        elif not content:
            messagebox.showerror("Virhe","Anna sisältö tai WiFi")
            return

        try:
            create_qr(
                text=content,
                out=out,
                kind=self.format_var.get(),
                dark=self.fg_color_btn['text'],
                light=self.bg_color_btn['text'],
                rounded=self.rounded_var.get(),
                logo=self.logo_path
            )
            messagebox.showinfo("Valmis",f"QR-koodi tallennettu: {out}")
        except Exception as e:
            messagebox.showerror("Virhe",str(e))

# -------------------------
# ENTRY POINT
# -------------------------
if __name__=="__main__":
    root=tk.Tk()
    app=QRGeneratorGUI(root)
    root.mainloop()
