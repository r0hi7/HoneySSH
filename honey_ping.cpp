#include <iostream>
#include <csignal>
#include <stdlib.h>
#include <string>
#include <sstream>
#include <arpa/inet.h>
#include <unistd.h>
using namespace std;
int packets;
//float time;
string ip;
clock_t begin,end;
float min=10000000,max=-1,sum=0;

void sigKillhandler(int sigterm){
	::end=clock();
	cout<<"\n--- "<<ip<<" ping statistics ---\n";
	cout<<packets+1<<" transmitted,"<<packets+1<<" received, 0% packet loss, time "<<(double)(::end-::begin)/CLOCKS_PER_SEC*10000000 << "ms\nrtt min/avg/max = "<<::min<<"/"<<(float)sum/packets<<"/"<<::max<<"/\n";
exit(1);
}
int main(int argc,char* argv[]){
	signal(SIGINT,sigKillhandler);
	if(argc==1){cout<<"Usage : ping [-c count] destination\n";exit(EXIT_FAILURE);}
	srand((unsigned)time(0));
	char ch[100];
	int ipIndex=-1;
	::begin=clock();
	for(int i=1;i<argc;++i)if(inet_pton(AF_INET,argv[i],(char *)ch))ipIndex=i;
	if(ipIndex==-1){cout<<"ping: unknown host "<<argv[argc-1]<<endl;exit(EXIT_FAILURE);}
	string ip(argv[ipIndex]);	
	cout<<"PING "<<ip<<" ("<<ip<<") 56(84) bytes of data.\n";
	int icmp_seq,ttl=(rand()%155)+100;
	string stmt = "64 bytes from "+ip+" ("+ip+"): ";
	for(int i=1;i<=100;++i){
		stringstream oss;
		float time = static_cast <float> (rand()) / static_cast <float> (RAND_MAX) + rand()%100+10;
	 	if(::min>time)::min=time;
		if(::max<time)::max=time;
		sum+=time;
		oss<<stmt<<"icmp_seq="<<i<<" ttl="<<ttl<<" time="<< time<<"ms";
		cout<<oss.str()<<endl;
		usleep(1000000);
		packets=i;
	}
}

/*
#include <csignal>
#include <cstdio>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <array>

using namespace std;

void modify_ping(string pingCmd) {
	std::array<char, 128> buffer;
	std::string pre,post;
	bool before=true;
	pingCmd.insert(pingCmd.find_last_of(' ')," -c 1 ");
	std::shared_ptr<FILE> pipe(popen(pingCmd.c_str(), "r"), pclose);
	if (!pipe) throw std::runtime_error("popen() failed!");
	while (!feof(pipe.get())) {
		if (fgets(buffer.data(), 128, pipe.get()) != NULL){
			string buf(buffer.data());
			if(before)pre+=buf;
			else post+=buf;		
			if(buf=="\n")before=false;
		}
	}
	cout<<pre.substr(pre.find_first_of("\n")+1,pre.size()-pre.find_first_of("\n"));
	pre.find_first_of()
}

void sigKillHandler(int singalNumber){
	cout<<"Caught signal handler";
}

int main()
{
	signal(SIGKILL,sigKillHandler);
	modify_ping("ping google.com");
	return 0;
}
*/
