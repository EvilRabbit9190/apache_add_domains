import time
from netmiko import ConnectHandler


HOST = None
USERNAME = None
PASSWORD = None


def get_params(host, username, password):
    global HOST, USERNAME, PASSWORD
    HOST = host
    USERNAME = username
    PASSWORD = password

# Функция будет вызываться на Backend и передавать параметры, которые передал пользователь
get_params(host='185.112.83.72', username='root', password='GO29QjsW0eBR')

domains = []
with open('domains/domains.txt', 'r', encoding='utf-8') as f:
    domains = f.read().split('\n')

print(domains)
print(len(domains))

# ==================================== идет запуск скрипта ==================================== #
start_time = time.time()

user_names = [
    'Anna12611', 'Anna12711'
]

linux = {
    'device_type': 'linux',
    'host': HOST,
    'username': USERNAME,
    'password': PASSWORD,
    "fast_cli": False,
}

ssh = ConnectHandler(**linux)
ssh.enable()


def settings_apache_http(dom, idx):
    code = """
<VirtualHost *:80>
    ServerName {}
    ServerAlias www.{}
    Redirect / https://{}
    DocumentRoot "/www/{}/www/public_html"
    <Directory "/www/{}/www/public_html">
        Options -FollowSymLinks +MultiViews -Indexes
        AllowOverride all
        Require all granted
    </Directory>
    ErrorLog "/www/{}/www/logs/error.log"
    CustomLog "/www/{}/www/logs/access.log" combined
</VirtualHost>
        """.format(dom, dom, dom, dom, dom, dom, dom)
    ssh.send_command(
        "echo '{}' >> '/etc/apache2/sites-available/www.{}.conf'".format(code, dom)
    )


def settings_apache_https(dom, idx):
    code = """
<IfModule mod_ssl.c>
<VirtualHost *:443>
    ServerName {}
    ServerAlias www.{}
    DocumentRoot "/www/{}/www/public_html"
    <Directory "/www/{}/www/public_html">
        Options -FollowSymLinks +MultiViews -Indexes
        AllowOverride all
        Require all granted
    </Directory>
    ErrorLog "/www/{}/www/logs/error.log"
    CustomLog "/www/{}/www/logs/access.log" combined

SSLCertificateFile /etc/letsencrypt/live/{}/cert.pem
SSLCertificateChainFile /etc/letsencrypt/live/{}/fullchain.pem
SSLCACertificateFile /etc/letsencrypt/live/{}/chain.pem
SSLCertificateKeyFile /etc/letsencrypt/live/{}/privkey.pem
SSLHonorCipherOrder off
SSLSessionTickets off
</VirtualHost>
</IfModule>
    """.format(dom, dom, dom, dom, dom, dom, dom, dom, dom, dom)
    ssh.send_command(
        "echo '{}' >> '/etc/apache2/sites-available/www.{}-ssl.conf'".format(code, dom)
    )


def settings_letsencrypt():
    code = """
Alias /.well-known/acme-challenge/ /var/www/letsencrypt/.well-known/acme-challenge/

<Directory "/var/www/letsencrypt/.well-known/acme-challenge/">
    Options None
    AllowOverride None
    ForceType text/plain
    Require all granted
    RedirectMatch 404 "^(?!/\.well-known/acme-challenge/[\w-]{43}$)"
</Directory>
    """
    ssh.send_command(
        f"echo '{code}' >> 'etc/apache2/conf-available/le.conf'"
    )


# # Удаление пользователей
# for (first_name, domain_site) in zip(user_names, domains):
#     create_user = ssh.send_command(
#         f'sudo deluser {first_name}'
#     )
#     print(create_user)

print('================================ Обновление ОС и установка Apache2 ================================')
# Обновление ОС и установка Apache2
try:
    update = ssh.send_command(
        'sudo apt update -y; sudo apt install apache2 -y')
    print(update)
except Exception as exc:
    print('[-] Exception при обновлении ОС: ', exc)

print('================================ Записываем домены в файл hosts ================================')
 # Записываем домены в файл hosts
try:
    domains_str = " www.".join(domains)
    ip_domains = f'{HOST} www.{domains_str}'.replace(',', '')
    print(ip_domains)
    add_domains_and_ip = ssh.send_command(command_string=f'echo "{ip_domains}" >> /etc/hosts',
                                          max_loops=1000)
except Exception as exc:
    print('[-] Exception при записывание доменов в файл hosts: ', exc)

print('================================ Создаем пользователей ================================')
# Создаем пользователей
try:
    for (first_name, domain_site) in zip(user_names, domains):
        domain = domain_site.replace(',', '')
        create_user = ssh.send_command(
            f'sudo useradd --create-home --home-dir /www/{domain} --shell /bin/bash --gid www-data --skel /etc/skel-www {first_name}'
        )
        print(create_user)
except Exception as exc:
    print('[-] Exception при создании пользователей: ', exc)

print('================================ Настраиваем Apache VirtualHost HTTP ================================')
# Настраиваем Apache VirtualHost
try:
    for idx_site_domain, site_domain in enumerate(domains):
        try:
            settings_apache_http(site_domain.replace(',', ''), idx_site_domain)
        except Exception as exc:
            print('Exception при настраивании Apache VirtualHost (2): ', exc)
            continue
except Exception as exc:
    print('[-] Exception при настраивании Apache VirtualHost(1): ', exc)

print('================================ Подключение конфигураций VirtualHost ================================')
# Подключение конфигураций VirtualHost
try:
    disabling_default = ssh.send_command('sudo a2dissite 000-default.conf')
    print('disabling_default: ', disabling_default)
    for domain_conf in domains:
        enabling_conf = ssh.send_command(f'sudo a2ensite www.{domain_conf}.conf')
        print('enabling_conf: ', enabling_conf)
    # enable_ssl = ssh.send_command('a2enmod ssl')
    # restart_apache2 = ssh.send_command('sudo systemctl restart apache2')
    # print('restart_apache2: ', restart_apache2)
except Exception as exc:
    print('[-] Exception при подключении конфигураций VirtualHost: ', exc)

# print("--- %s Время выполнения в seconds ---" % (time.time() - start_time))


print('================================ Настраиваем Apache VirtualHost HTTPS ================================')
 # Настраиваем Apache VirtualHost
try:
    for idx_site_domain, site_domain in enumerate(domains):
        try:
            print('idx_site_domain: ', idx_site_domain)
            settings_apache_https(site_domain.replace(',', ''), idx_site_domain)
        except Exception as exc:
            print('Exception при настраивании Apache VirtualHost (2): ', exc)
            continue
except Exception as exc:
    print('[-] Exception при настраивании Apache VirtualHost(1): ', exc)

=======================================================================================
# # # sudo ufw enable

print('================================ Start Обновление и установление программ для HTTPS сертификата  ================================')

# Обновление ОС и установка Apache2
try:
    # https_install = ssh.send_command(
        # 'sudo apt install certbot python3-certbot-apache -y; sudo apt install snapd; sudo snap install --classic certbot'
    # )
    # print(https_install)
    for domain_conf in domains:
        print(domain_conf)
        try:
            res = ssh.send_command(f'sudo certbot certonly --apache -d avax.{domain_conf} -d www.avax.{domain_conf}') #------> +
            print('res: ', res)
        except Exception as exc:
            continue
            # print('Exception при подключении конфигураций VirtualHost HTTPS 2', exc)
except Exception as exc:
    print('[-] Exception при подключении конфигураций VirtualHost HTTPS 1: ', exc)


try:
    for domain_conf in domains:
        try:
            enabling_conf_ssl = ssh.send_command(f'sudo a2ensite www.{domain_conf}-ssl.conf')
            print('enabling_conf_ssl: ', enabling_conf_ssl)
        except Exception:
            print('Exception 2')
            continue
    reload_apache2 = ssh.send_command(f'systemctl reload apache2')
    print('reload_apache2: ', reload_apache2)
    restart_apache2 = ssh.send_command(f'sudo systemctl restart apache2')
    print('restart_apache2: ', restart_apache2)
except Exception as exc:
    print('Exception при подключении конфигураций VirtualHost HTTPS 2', exc)


# print('======================================= END =======================================')
# ssh.send_command('ufw allow 443')
# ssh.send_command('a2enmod ssl')

# try:
#     # ssh.send_command('mkdir /var/www/letsencrypt')
#     # ssh.send_command('chown -R www-data:www-data /var/www/letsencrypt')
#     # ssh.send_command('touch /etc/apache2/conf-available/le.conf')
#     # ssh.send_command('apt install certbot -y')

#     # settings_letsencrypt()
#     for idx_site_domain, site_domain in enumerate(domains):
#         try:
#             letsencrypt = ssh.send_command(f'certbot certonly --webroot -w /var/www/letsencrypt -d {site_domain} -d www.{site_domain}')
#             print('letsencrypt; ', letsencrypt)
#         except Exception as exc:
#             print('Exception 2-1', exc)
# except Exception as exc:
#     print('[-] Exception 2', exc)

# try:
#     for idx_site_domain, site_domain in enumerate(domains):
#         letsencrypt = ssh.send_command(f'a2ensite www.{site_domain}-ssl.conf')
#         print('letsencrypt; ', letsencrypt)
# except Exception as exc:
#     print('[-] Exception 2')

# try:
#     for idx_site_domain, site_domain in enumerate(domains):
#         try:
#             ssh.send_command(f'certbot certonly --dry-run --webroot -w /var/www/letsencrypt -d {site_domain} -d www.{site_domain}')
#             # certbot_certonly = ssh.send_command(f'certbot certonly --webroot -w /var/www/letsencrypt -d {site_domain} -d www.{site_domain}')
#             # print('certbot_certonly: ', certbot_certonly)
#             # a2ensite = ssh.send_command(f'a2ensite {site_domain}-ssl.conf')
#             # print('a2ensite: ', a2ensite)
#         except Exception as exc:
#             print('Exception при настраивании Apache VirtualHost (2): ', exc)
#             continue
#         # ssh.send_command('a2enmod ssl')
# except Exception as exc:
#     print('[-] Exception при настраивании Apache VirtualHost(1): ', exc)


# #  Disable domains-ssl.conf
# try:
#     for domain_conf in domains:
#         try:
#             command = ssh.send_command(f'sudo a2dissite www.{domain_conf}-ssl.conf')
#             # command = ssh.send_command(f'sudo a2ensite www.{domain_conf}.conf')
#             print('command: ', command)
#         except Exception as exc:
#             print('Exception 1: ', exc)
#             continue
# except Exception as exc:
#     print('[-] Exception 2: ', exc)

# try:
#     try:
#         ssh.send_command('sudo apt-get install php -y')
#     except Exception:
#         print('Произошла ошибка при установлениии php')
#     try:
#         ssh.send_command('sudo apt-get install php-curl -y')
#     except Exception:
#         print('Произошла ошибка при установлениии php-curl')
# except Exception as exc:
#     print('[-] Exception при установление php зависимостей: ', exc)

# Установка PHP
#       sudo apt-get install apache2 php libapache2-mod-php7.0 mysql-server php-mbstring php7.0-mbstring phpmyadmin
#       sudo service apache2 restart


# # # [certbot renew --dry-run] --> для обновленияW
# # # [sudo certbot --apache] --> получение сертификатов для всех доменов


# for domain in domains:
#     # command = f'sudo certbot certonly --apache -d {domain} -d www.{domain}'
#     command = f'sudo certbot certonly --apache -d {domain} -d www.{domain}'
#     res = ssh.send_command(command)
#     print(res)
#     # with open('command.txt', 'a', encoding='utf-8') as file:
#         # file.write(command + '\n')
#         # file.close()
