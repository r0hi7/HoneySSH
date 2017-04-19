/root/HoneySSH/honsshctrl.sh stop
/root/HoneySSH/honsshctrl.sh clean 

fuser -k 22/tcp
lxc delete system -f  
lxc launch ubuntu16 system
sleep 5
lxc stop system 
lxc network attach systemBr system default eth0
lxc start system
sleep 15 
echo "Done"

ip=$(lxc info system | grep -m1 "eth0..inet" | cut -f 3)
sys_ip=$(lxc info sys | grep -m1 "eth0..inet" | cut -f 3)


lxc exec system -- sed -i '/PasswordAuthentication no/c\PasswordAuthentication yes' /etc/ssh/sshd_config
lxc exec system -- sed -i '/PermitRootLogin/c\PermitRootLogin yes' /etc/ssh/sshd_config > /dev/null

lxc exec system  -- bash -c "echo -e \"fakeroot\nfakeroot\" | passwd root"
lxc exec system -- service ssh restart 
#/root/HoneySSH/setup_ssh_redirection_honeypot.sh system $sys_ip

sed -i "/honey_ip =/c\honey_ip = $ip" /root/HoneySSH/honssh.cfg
/root/HoneySSH/honsshctrl.sh start


