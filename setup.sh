#!/bin/bash

function color_print {
    if [ "$1" == "green" ];then echo -e "\e[92m" $2 "\e[0m\c";fi
    if [ "$1" == "red" ];then   echo -e "\e[91m" $2 "\e[0m\c";fi
    if [ "$1" == "yellow" ];then echo -e "\e[33m" $2 "\e[0m\c";fi
}

function invalidIp {
    if [[ $1 =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then return 1;
    else return 0;
    fi
}

function setup_ssh_redirection_system {
    echo -e "[*]\c";color_print "yellow" "Installing ssh redirection system  to trap the attacker"
    lxc info pc1;
    if [ $? -eq 0 ];then echo -e "[*]\c";color_print "red" "Conatainer Named with PC1 Alredy found..Removing\n";
        lxc stop pc1;
        lxc delete pc1;
    fi
    lxc launch ubuntu16 pc1;
    lxc stop pc1;
    echo -e "[*]\c"; color_print "green" "Adding PC1 to bridge [systemBr]";
    lxc network attach systemBr pc1 default eth0;
    lxc start pc1;
    sleep 5
    pc1_ip=$(lxc info pc1 | grep -m1 "eth0..inet" | cut -f 3)
    echo -e "[*]\c"; color_print "green" "PC 1 got the IP ";color_print "red" $pc1_ip
    
    lxc exec pc1 -- sed -i '/PasswordAuthentication no/c\PasswordAuthentication yes' /etc/ssh/sshd_config
   
    lxc exec pc1 service sshd restart;
    lxc exec pc1 -- groupdel admin
  
    lxc exec pc1 -- useradd -m admin -s /bin/bash
    lxc exec pc1 -- bash -c "echo -e \"admin\nadmin\" | passwd admin"
}


#this function secure honeypot abusing by blocking all outgoing ping and ssh connection
function secure_honeypot {
    echo -e "[*]\c"; color_print "yellow" "Adding Rules to secure honeypot";
}

function setup_linux {
    echo -e "[*]\c";color_print "green" "We will install lxc based container to run the traget system\n"
    dpkg -s lxd
    if [ $? -ne 0 ]
    then
        echo -e "[*]\c";color_print "red" "lxd not installed"
        color_print "green" "lxd will be installed"
        apt-get install lxd
        lxd init
    fi
    echo -e "[*]\c";color_print "green" "Chosen Imgae Ubuntu _ 16.04 x86]\n"
    lxc image copy ubuntu:x local: --alias ubuntu16
    lxc info system
    if [ $? -eq 0 ];then echo -e "[*]\c";color_print "red" "Conatainer Named with system Alredy found..Removing\n";
        lxc stop system;
        lxc delete system;
    fi
    lxc launch ubuntu16 system
    lxc stop system
    echo -e "[*]\c";color_print "green" "Container is not attached to the Network..Bridging it[honeypotBr]\n"
    echo -e "[*]\c";color_print "yellow" "Checking if honeypot[systemBr] Bridge Exists or not"
    lxc network show systemBr
    if [ $? -ne 0 ]
    then
        echo -e "[*]\c";color_print "green" "Bridge donot Exists creating"
        lxc network create systemBr
    fi
    lxc network attach systemBr system default eth0
    lxc start system
    #wait for the system to get bridge
    sleep 5
    container_ip=$(lxc info system | grep -m1 eth0..inet | cut -f 3)
    #echo $container_ip
    if ! invalidIp container_ip;then echo -e "[*]\c";color_print "red" "Unbale to fetch the IP of the container !\nSet it Manually if Possible";exit;fi
    echo -e "[*]\c";color_print "green" "HoneyPot IP";color_print "red" $container_ip;echo -e "\n";
    container_port=22
    #sed -i "/ssh_addr =/c\ssh_addr = $ssh_addr" honssh.cfg
    #sed -i "//c\"

    #sed -i "/client_addr = /c\client_addr = $honey_ip" honssh.cf
    sed -i "/honey_ip =/c\honey_ip = $container_ip" honssh.cfg
    sed -i "/honey_port =/c\honey_port = $container_port" honssh.cfg

    lxc exec system  -- sed -i '/PasswordAuthentication no/c\PasswordAuthentication yes' /etc/ssh/sshd_config
    #lxc exec system cat /etc/ssh/sshd_config
    lxc exec system service sshd restart;
    lxc exec system -- groupdel admin
    echo -e "[*]\c";color_print "green" "Machine created, Enter the user to create ";read username;
    echo -e "[*]\c";color_print "green" "Enter password for the $username ";read password;
    lxc exec system -- useradd -m $username -s /bin/bash
    lxc exec system -- bash -c "echo -e \"$password\n$password\" | passwd $username"
    echo -e "[$username]\nreal_password = $password\nfake_passwords = " > users.cfg
    echo -e "[*]\c";color_print "green" "user.cfg";color_print "yellow" "created, Please add fake password for $username\n"

    setup_ssh_redirection_system;
    bash ./setup_ssh_redirection_honeypot.sh system $pc1_ip;
    bash ./setup_ssh_redirection_honeypot.sh pc1 $container_ip;

}

function setup_windows {
    echo -e "[*]\c";color_print "yellow" "For the Traget Windows system .. Virtual Box Will be used\n"
    echo -e "[*]\c";color_print "yellow" "Checking If VBox is installed or not\n"
    dpkg -s virtualbox
    if [ $? -ne 0 ];then echo -e "[*]\c";color_print "red" "Virtual Box not found installing\n";
        apt-get install virtualbox virtualbox-qt -y;
        if [ $? -eq 0 ];then echo -e "[*]\c";color_print "red" "Unbale to install virtual box ... Quiting";exit ;fi
        echo -e "[*]\c";color_print "yello" "Checking vboxmanage\n";which vboxmanage;
        if [ $? -ne 0 ];then color_print "red" "Vbox Missing .. Exiting";exit;fi
    fi
    echo -e "[*]\c";color_print "green" "VBox Successfully installed"
    ls win7.zip
    if [ $? -ne 0 ];
    then
        echo -e "[*]\c";color_print "red" "Windows image file not found locally\n"
        echo -e "[*]\c";color_print "yellow" "Downloading windows image file.. Please Be patient\n"
        url="https://az412801.vo.msecnd.net/vhd/VMBuild_20141027/VirtualBox/IE10/Windows/IE10.Win7.For.Windows.VirtualBox.zip"
        wget $url -O win7.zip
        echo -e "[*]\c";color_print "yellow" "Unzipping downloaded ova file"
        unzip win7.zip
    fi
    #unzip win7.zip
    #mv 'IE10 - Win7.ova' win7.ova
    vboxmanage list vms | grep win7
    if [ $? -ne 0 ];then
        #rm -f /root/VirtualBox VMs/Win7/Win7.vbox
        vboxmanage import --vsys 0 --cpus 1 --memory 2048 --vmname Win7 'IE10 - Win7.ova';
        #vboxmanage natnetwork add --netname "natnet1" --network "192.168.15.0/24" --enable --dhcp on
        #vboxmanage modifyvm Win7 --nic1 natnetwork --nat-network1 natnet1
        vboxmanage modifyvm Win7 --nic1 nat
        #assuming vboxnet0 will be created
        #vboxmanage hostonlyif create
        vboxmanage modifyvm Win7 --nic2 hostonly --hostonlyadapter1 vboxnet0
    fi
    #assuming the first ip is of VBOXNET hostonlyadapter
    honey_ip=$(vboxmanage guestproperty enumerate Win7 | grep -m1 IP | grep -E -o "([0-9]{1,3}[.]){3}[0-9]{1,3}")
    honey_port=22;
    sed -i "/honey_ip =/c\honey_ip = $honey_ip" honssh.cfg
    sed -i "/honey_port =/c\honey_port = $honey_port" honssh.cfg
    echo -e "[*]\c";color_print "yellow" "The configuration has been setup Please Install bitwise ssh server in Windows Machine"
}

if [ $EUID -ne 0 ];then color_print "red" "Please Run as Root..\n";exit;fi

echo -e "[*]\c"; color_print "green" "HoneySSH Config file missing creating one"
ls honssh.cfg
if [ $? -ne 0 ];then cp honssh.cfg.default honssh.cfg;fi

echo -e "[*]\c";color_print "green" "Enter the Address to bind the HoneySSH to [0.0.0.0]"
read ssh_addr
if [[ -z "${ssh_addr// }" ]];then  ssh_addr="0.0.0.0";fi
if invalidIp $ssh_addr
then
    echo -e "[*]\c";color_print "red" "Invalid IP address Quiting"
    exit
fi

echo -e "[*]\c";color_print "green" "Enter the Port to bind the HoneySSH to [22]"
read ssh_port
if [[ -z "${ssh_port// }" ]];then ssh_port=22;fi

sed -i "/ssh_addr =/c\ssh_addr = $ssh_addr" honssh.cfg
sed -i "/ssh_port =/c\ssh_port = $ssh_port" honssh.cfg

echo -e "[*]\c";color_print "green" "Enter the HoneyPot sensor Name[sshProxy]"
read sensor_name
if [[ -z "${name// }" ]];then sensor_name="sshPorxy";fi

sed -i "/sensor_name = /c\sensor_name = $sensor_name" honssh.cfg
sed -i "/client_addr = /c\client_addr = $ssh_addr" honssh.cfg

echo -e "[*]\c";color_print "green" "Please specify the type of HoneyPot to build Linux/Windows [Linux]"
read target

if [[ -z "${target// }" ]];then target="Linux";fi
if [ "$target" == "Linux" ];then setup_linux ;fi
if [ "$target" == "Windows" ]; then setup_windows ;fi
