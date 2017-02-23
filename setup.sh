#!/bin/bash
function color_print {
  if [ "$1" == "green" ];then echo -e "\e[92m" $2 "\e[0m\c";fi
  if [ "$1" == "red" ];then   echo -e "\e[91m" $2 "\e[0m\c";fi
}

function invalidIp {
  if [[ $1 =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then return 1;
  else return 0;
  fi
}

function setup_linux {
  echo -e "[*]\c";color_print "green" "We will install lxc based container to run the traget system"
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
  lxc network create honeypotBr
  lxc network attach honeypotBr system eth0
  lxc start system
  #wait for the system to get bridge
  sleep 5
  container_ip=$(lxc info system | grep -m1 eth0..inet | cut -f 3)
  #echo $container_ip
  if ! invalidIp container_ip;then echo -e "[*]\c";color_print "red" "Unbale to fetch the IP of the container !\nSet it Manually if Possible";exit;fi
  color_print "green" "HoneyPot IP";color_print "red" $container_ip
  container_port=22
  #sed -i "/ssh_addr =/c\ssh_addr = $ssh_addr" honssh.cfg
  sed -i "/honey_ip =/c\honey_ip = $container_ip" honssh.cfg
  sed -i "/honey_port =/c\honey_port = $container_port" honssh.cfg
}

function setup_windows {
  color_print "red" "todo"
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
read name
if [[ -z "${name// }" ]];then name="sshPorxy";fi

echo -e "[*]\c";color_print "green" "Please specify the type of HoneyPot to build Linux/Windows [Linux]"
read target

if [ "$target" == "Linux" ];then setup_linux ;fi
