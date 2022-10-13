# Author: Helmsys

from time import sleep
from urllib3 import disable_warnings
from requests import Session
from bs4 import BeautifulSoup
from threading import Thread
import json

disable_warnings()
exit_ = False
new_inbox_message = False
class TempMail:
    def __init__(self) -> None:
        self.verify_code = ""
        self.cookies = {}
        self.subject = None
        self.content = None
        self.from_ = None
        self.__header = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.81 Safari/537.36",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "Connection": "keep-alive",
                "Host": "www.fakemail.net",
                "Referer": "https://www.fakemail.net/"
            }
        self.getPHPSESSID()
        self.createAccount()
        Thread(target=self.inboxRefresh,daemon=True).start()

    def getPHPSESSID(self):
        print("Cookie Alınıyor...")
        with Session() as session:
            self.cookies.update(session.get("https://www.fakemail.net/",verify=False).cookies.get_dict())

    def createAccount(self):
        with Session() as session:
            self.__header.update({"Cookie":f"PHPSESSID={self.cookies['PHPSESSID']}"})
            self.cookies.update(session.get("https://www.fakemail.net/index/index",verify=False,headers=self.__header).cookies.get_dict())
            return

    def inboxRefresh(self):
        global new_inbox_message,exit_
        with Session() as session:
            self.__header.update({"Cookie":f"PHPSESSID={self.cookies['PHPSESSID']}; TMA={self.cookies['TMA']}; wpcc=dismiss"})
            while exit_ != True:
                # print(f"exit_ = {exit_}")
                __response = session.get("https://www.fakemail.net/index/refresh",verify=False,headers=self.__header).text.replace(u'\ufeff','')
                __subject = json.loads(__response)[0]['predmet']
                __from = json.loads(__response)[0]['od']
                __content = session.get("https://www.fakemail.net/email/id/2",verify=False,headers=self.__header).content
                
                while __from == 'Fake Mail <Admin@FakeMail.net>':
                    __response = session.get("https://www.fakemail.net/index/refresh",verify=False,headers=self.__header).text.replace(u'\ufeff','')
                    __subject = json.loads(__response)[0]['predmet']
                    __from = json.loads(__response)[0]['od']
                    __content = session.get("https://www.fakemail.net/email/id/2",verify=False,headers=self.__header).content
                    if __from != 'Fake Mail <Admin@FakeMail.net>':
                        self.from_ = __from.replace("<","").replace(">","")
                        self.subject = __subject
                        self.content = __content
                        new_inbox_message = True
                    sleep(1)

                if new_inbox_message:
                    print("inboxtan çıkıldı")
                    exit_ = True

                sleep(1)

class TelegramBot:
    def __init__(self,api_key:str) -> None:
        self.__getUPDATES = f"https://api.telegram.org/bot{api_key}/getUpdates"
        self.__sendMESSAGE = f"https://api.telegram.org/bot{api_key}/sendMessage"
        self.__deleteGetUPDATES=f"https://api.telegram.org/bot{api_key}/getUpdates" # offset=343126593 +1
        self.__commands = ["/help","/create_mail"]
        self.__users = {}
        self.__before_messageID = 0
        Thread(target=self.__bot).start()

    def __bot(self):
        global new_inbox_message
        while True:
            try:
                self.__getusers()
                self.__parseMessage(recv=self.__users["users"]["text"])
                if new_inbox_message:
                    self.__seeInbox(new_inbox=new_inbox_message)
            except KeyError:
                pass

    def __getusers(self):
        with Session() as session:
            __response = session.get(self.__getUPDATES).json()
            # print(__response['result'])
            for i in range(len(__response['result'])):
                # if i == 99:
                #     for j in range(i):
                #         session.get(self.__deleteGetUPDATES,params={"offset":__response['result'][j]["update_id"]+1})
                self.__users.update(
                    {
                        "users":{
                            "msg_id":__response['result'][i]["message"]["message_id"],
                            "id":__response['result'][i]["message"]["chat"]["id"],
                            "text":__response['result'][i]['message']['text'],
                            "name":__response['result'][i]['message']['chat']['first_name']
                            }
                    })
            if not __response['result'] == []:
                for j in range(len(__response['result'])):
                    session.get(self.__deleteGetUPDATES,params={"offset":__response['result'][j]["update_id"]+1})
    
    def __parseMessage(self,recv:str):
        if self.__before_messageID < int(self.__users["users"]["msg_id"]):
            if recv == "/start" or recv == "/commands":
                self.__sendMessage(chat_id = self.__users["users"]["id"], text = f"{self.__commandannotations}")
            
            for i in self.__commands:
                if i in recv:
                    self.__sendMessage(chat_id = self.__users["users"]["id"], text = recv)
            
            self.__before_messageID = int(self.__users["users"]["msg_id"])

    def __seeInbox(self,new_inbox:bool):
        global new_inbox_message
        with Session() as session:
            __data = {
                "chat_id":self.__users["users"]["id"],
                "reply_to_message_id":self.__users["users"]["msg_id"],
                "text": None,
                "parse_mode": "HTML",
            }
            if new_inbox:
                soup = BeautifulSoup(tm.content,"lxml")
                inbox = f"<code><strong>{'─'*(len(tm.from_)//2) if tm.from_!=None else '─'*5}INBOX{'─'*(len(tm.from_)//2) if tm.from_!=None else '─'*5}</strong></code>\n<strong>Kimden:</strong> {tm.from_}\n<strong>Başlık:</strong> {tm.subject}\n<strong>İçerik:</strong> {''.join(i.text for i in soup.find_all('div')) if tm.from_!=None else None}"
                __data.update({"text":inbox})
                session.get(self.__sendMESSAGE,data=__data)
                new_inbox_message = False
    
    def __sendMessage(self,chat_id:int,text:str,parse_mode="HTML"):
        global exit_,tm
        try:
            with Session() as session:
                
                data = {
                    "chat_id":chat_id,
                    "reply_to_message_id":self.__users["users"]["msg_id"],
                    "text": text,
                    "parse_mode": parse_mode,
                }
                if text == '/create_mail':
                    exit_ = False
                    tm = TempMail()
                    mail = tm.cookies['TMA'].replace('%40','@')
                    data.update({"text":f"<code><strong>─────MAIL CREATED─────</strong></code>\n🔸<b>Mail: {mail}</b>\n<b>🔸Gelen Kutusu Oluşturuldu</b>\n<b>🔸Posta bekleniyor...</b>"})

                if text == "/help":
                    data.update({"text":self.__help__})

        except NameError:
            session.post(self.__sendMESSAGE,data=data.update({"text":"Önce Mail oluşturulması gerek"}))
        finally:
            session.post(self.__sendMESSAGE,data=data)
            self.__users.clear()

    @property
    def __commandannotations(self):
        return "<code><strong>──Komutlar──\n</strong></code>"+"\n".join(f"<i>🔸{i}</i>" for i in self.__commands)+"\n"+f"<code>{'─'*13}</code>"

    @property
    def __help__(self):
        __mylink__ = lambda x:f"<a href='https://github.com/Arif-Helmsys'>{x}</a>"
        __about__ = f"""
Bot, bir temp mail servisini kullanır.

<i>🔸/create_mail</i> 〰 <b>Bu komut mail adresi oluşturmaya yarar.</b>
<i>🔸 Mail adresine bir gönderi geldiği vakit bildirim alacaksınız</i>
<i>🔸 Her işlem için yalnızca <b>1(Bir) adet mail verilir.</b></i>
<i>🔸 Başka işlem yapacaksanız yeniden mail oluşturmalısınız.</i>
⬇ Bot {__mylink__('Helmsys')} tarafından yazılmıştır ⬇"""
        return f"<code><strong>────────Bot Hakkında Bilgiler────────\n</strong></code>{__about__}"

if __name__ == "__main__":
    __API__ = json.loads(open("tempMail/tokens.json", mode="r", encoding="utf-8").read())["token"]
    TelegramBot(__API__)
