#!/usr/bin/env python
#-*- coding: utf-8 -*-
 
# mqBackup Tool V1.3 Beta
# @site: http://mqbackup.maqas.net/
# @author: Hakan Mustak & Kamil Ors
# @mail: info@maqas.net
# Revised on 22/10/2012
# Created on 10/03/2012
 
#Betik içinde İhtiyaç duyduğumuz paketler
import os, time, MySQLdb, tarfile, shutil, smtplib
from os.path import getsize
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText

 
#AYARLAR - (Kullanıcı tarafından değiştirilebilir ayarlar)
#---------------------------------------------------------------------------
#MySQL kurulu bilgisayar
dbserver = "localhost"
#MySQL kullanıcı adı
dbUser = "root"
#MySQL şifresi
dbPasswd = "PASSWORD"
#MySQL Backup Yolumuz
yedekYolu = "/home/redshark/backup/www/"
#Web dizini Yolumu
webYolu = r"/var/www/"
#Eski dosta silinme Limit Gün sayısı
limit = 10
#Mail Bilgileri
mailUser = "hmustak@gmail.com"
mailPasswd = "PASSWORD"
mailFrom = "hakan@mustak.org"
mailTo = "hmustak@gmail.com"
#----------------------------------------------------------------------------
 
# Kullanıcı tarafından değiştirilmesi ÖNERİLMEYEN ayarlar
#---------------------------------------------------------------------------
#Tarih-Saat bilgisi
zaman = time.strftime("%Y-%m-%d-%H-%M")
#DB yedekyolu
dbYedekYolu = r"%smysql/%s/" % (yedekYolu, time.strftime("%Y-%m-%d"))
#WebDizini Backup Yolumu
webYedekYolu = r"%sweb/%s/" % (yedekYolu,time.strftime("%Y-%m-%d"))
#Database isimlerini koyacağımız liste
dbListe = []
#Database dosyalarımızın boyutları
bilgiBoyut = []
#Silinen dizin-dizinler
silinenDizin = []
#---------------------------------------------------------------------------
#Önce temizlik...
os.system("clear")

#DB isimlerini listelere yerleştiriyoruz
def dbListeOlustur():
    #Bilgilendirmeyi yapalım
    print " => Veritabanı bağlantısı sağlanıyor"
    #Database'e bağlanamazsak scripti durduralım
    try:
        # Database bağlantısını yapıyoruz
        dataCon = MySQLdb.connect(dbserver,dbUser,dbPasswd)
        # Nesnemizi oluşturuyoruz
        dbNesne = dataCon.cursor()
        # Databaselerimizi çekelim
        dbNesne.execute("show databases")
    
        # Ve Databaselerimizi yedekleyelim
        for database in dbNesne.fetchall():
            #Yedeklenmesini istemediğimiz VT'leri hariç bırakalım
            if (database[0]!="information_schema")and(database[0]!="mysql"):
                #Yedek hazırlayan fonksiyonumuzu çağırıyoruz
                dbListe.append(database[0])
    except:
        print "\n"
        print "\t******************************************************"
        print "\t\033[1;;31mDatabase bağlantı hatası!\033[0m"
        print "\t\033[1;;31mBağlantı bilgilerinizi kontrol edip tekrar deneyin\033[0m"
        print "\t******************************************************\n\n"

        exit()

#DB lerimizi sıkıştırıp Dump ediyoruz
def dbYedekle():
    #Bilgilendirmeyi yapalım
    print " => SQL Yedek dosyaları oluşturuluyor"
    #Veritabanı listesini çekiyoruz
    for liste in dbListe:
        #Dosya adını oluşturuyoruz
        dbYedekDosya = r"%s_%s_SQL_backup.sql" % (zaman,liste)
        #MysqlDump komutumuzu işleterek sql dosyamızı oluşturuyoruz
        os.system("mysqldump --skip-lock-tables -u%s -p%s %s > %s%s" % (dbUser, dbPasswd, liste, dbYedekYolu, dbYedekDosya))
        #Oluşturduğumuz sql dosyamızı sıkıştırıyoruz
        os.system("gzip -9 %s%s" % (dbYedekYolu, dbYedekDosya))

#Yedeklenecek DB'leri gösterir
def dbListeGoster():
    #Bilgilendirmeyi yapalım
    print "*** Veritabanları yedeklendi"
    #Dosya ölçü ve isimlerini çekelim
    for dosya in os.listdir(dbYedekYolu):
        #dosya ve yolunu bir değişkene atamalıyız(daha okunur oluyor)
        yol = r"%s%s" % (dbYedekYolu,dosya)
        #sonuçları listemize ekliyoruz
        bilgiBoyut.append("[vt][%s kb] %s" % (round((getsize(yol)/1024.0),2) ,dosya))

#Yedeklenecek web ana dizinini burada sıkıştırıp yedekliyoruz
def dizinYedekle(source, target):
    #yedek dosyamızın adını oluşturuyoruz
    dosyaYol = "%s%s%s"%(target,zaman,".tar.gz")
    #Klasör sıkıştırmak için tar modülünü kullanıyoruz
    tar = tarfile.open(dosyaYol, "w:gz")
    #Üstte oluşturduğumuz dosyaya aşağıdaki adresi ekliyoruz
    tar.add(source)
    #İşimiz bitince ışıkları söndürelim/uygulamaları kapatalım
    tar.close()
    #yedeklenen dizinlerin bilgilerini daha sonra kullanmak üzere listeye ekliyoruz
    bilgiBoyut.append("[dizin][%s mb] %s" % (round(((getsize(dosyaYol)/1024.0)/1024),2) ,dosyaYol))
    #Uygulama ne aşamada kullanıcıya bilgi verelim
    print "*** Web dizini yedeklendi"

#Belli bir süre sonunda ihtiyacı biten yedekleri silmeliyiz
def eskiDizinSil(sil,tip):
    #Yedeğin silineceği dizindeki klasörleri listeliyoruz
    for dizin in os.listdir(sil):
        #silinen dosyaadını taşıyacağımız değişken
        silinenTip=""
        #limit gün sayısından toplam saniyeyi hesaplıyoruz
        limitSN = limit * 86400
        #Silme aşamasında hata oluşabiliyor, oluşursa devam edelim
        try:
            #Dizinin ömrü verilen limitten fazla ise (default:10gün)
            if (os.stat(sil+dizin).st_ctime < (time.time()-limitSN)):
                #Silme bilgisi için kayıt oluşturuyoruz
                silinenTip = "[%s] %s"%(tip,dizin)
                #silme bilgisini kayıt listesine ekliyoruz
                silinenDizin.append(silinenTip)
                #Dizini tüm alt dizin ve dosyaları ile birlikte silitoruz
                shutil.rmtree(sil+dizin)
        except :
            #Hata varsa, devam et
            pass

def bilgi():
    #Mail gönderilecek gövde
    metin = "" + "\n\n"
    metin = metin + "Yedeklenen Dosyalar ve büyüklükleri" + "\n"
    metin = metin + "----------------------------------------------------------------------" + "\n"
    #Yedekleme bilgileri hazırlanıyor
    for liste in bilgiBoyut:
        metin = metin + liste + "\n"
    metin = metin + "----------------------------------------------------------------------" + "\n\n"
    metin = metin + "Silinen Dizinler" + "\n"
    metin = metin + "----------------------------------------------------------------------" + "\n"
    #Silme bilgileri hazırlanıyor
    for dizin in silinenDizin:
        metin = metin + dizin + "\n"
    metin = metin + "----------------------------------------------------------------------" + "\n\n"

    #MIMEMultipartı hazırlamaya başlıyoruz
    posta = MIMEMultipart()
    posta['Subject'] = "%s : Günlük Yedekleme Tamamlanmıştır" % (zaman)
    posta['From'] = mailFrom
    posta['To'] = mailTo
    mesaj = metin
    posta.attach(MIMEText(mesaj))

    #Mail göndermek üzere gmaile bağlanıyoruz (Günlük limit 500)
    try:
        smtpserver = smtplib.SMTP("smtp.gmail.com",587)
        smtpserver.ehlo()
        smtpserver.starttls()
        smtpserver.ehlo
        smtpserver.login(mailUser, mailPasswd)
        smtpserver.sendmail(mailUser, mailTo, posta.as_string())
        smtpserver.close()
        mailstatus = 1
    except:
        mailstatus = 0
        pass

    #Mail gönderdikten sonra sonuçları ekrana basalım
    print "\n"
    print "Yedeklenen Dosyalar ve büyüklükleri"
    print "--------------------------------------------------------------------"
    #Bilgi Listemizi gösterelim
    for liste in bilgiBoyut:
        print liste
    print "--------------------------------------------------------------------\n"
    print "Silinen Dizinler"
    print "--------------------------------------------------------------------"
    #Bilgi Listemizi gösterelim
    for dizin in silinenDizin:
        print dizin
    print "--------------------------------------------------------------------\n"
    if (mailstatus):
        print "Bilgilendirme maili gönderilmiştir : \033[1;;31m%s\033[0m" % (mailUser)
        print "\n"
    else:
        print "\033[1;;31m%s adresine bilgilendirme maili gönderilememiştir\033[0m" % (mailUser)
        print "\033[1;;31mLütfen email bağlantı bilgilerinizi kontrol ediniz\033[0m"
        print "\n"
        
#Dizin oluşturma fonksiyonumuz
def dizinOlustur(dizin):
    os.mkdir(dizin)

# Backup altındaki base yedek dizinimizi oluşturalım
if os.path.isdir(yedekYolu+"mysql/") == False:
    dizinOlustur(yedekYolu+"mysql/")
if os.path.isdir(yedekYolu+"web/") == False:
    dizinOlustur(yedekYolu+"web/")

#Günlük yedekleme yapılmış mı? Kontrol ve yedekleme alanımız
if os.path.isdir(dbYedekYolu) == False:
    #Veritabanı ve Web dizini için yedeklenecek dizini oluşturalım
    dizinOlustur(dbYedekYolu)
    dizinOlustur(webYedekYolu)

    #Veritabanı yedekleme işlemleri
    dbListeOlustur()
    dbYedekle()
    dbListeGoster()

    #Web dizini yedekleme işlemleri
    dizinYedekle(webYolu,webYedekYolu)

    #Eski dizinleri silme vakti
    eskiDizinSil(yedekYolu+"mysql/","vt")
    eskiDizinSil(yedekYolu+"web/","web")

    #Yedekleme sonuç gösterme/gönderme bilgileri
    bilgi()

else:
    print "Bugün (%s) yedeğiniz alınmış gözüküyor" % (time.strftime("%d-%m-%Y"))

