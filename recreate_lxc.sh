lxc stop system
lxc copy system system2
lxc delete system 
lxc copy system2 system
lxc network attach systemBr system default eth0
lxc start system
sleep 5 
echo "Done"

ip=$(lxc info system | grep -m1 "eth0..inet" | cut -f 3)
sys_ip=$(lxc info sys | grep -m1 "eth0..inet" | cut -f 3)


lxc exec system -- sed -i '/PasswordAuthentication no/c\PasswordAuthentication yes' /etc/ssh/sshd_config
lxc exec system -- sed -i '/PermitRootLogin/c\PermitRootLogin yes' /etc/ssh/sshd_config > /dev/null

/root/HoneySSH/setup_ssh_redirection_honeypot.sh system $sys_ip

sed -i "/honey_ip =/c\honey_ip = $ip" honssh.cfg
/root/HoneySSH/honsshctrl.sh stop
/root/HoneySSH/honsshctrl.sh clean 
/root/HoneySSH/honsshctrl.sh start


