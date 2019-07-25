import os
import subprocess
from os import path
import wget
import progress.spinner
import time
import threading
import sys
import argparse
import re
from pwd import getpwuid
from grp import getgrgid
import random
import logging

#Argument Parser
parser = argparse.ArgumentParser()
parser.add_argument('-t',default='1',choices=['1','2','3'],type=str,help='Enter type of installation.')
parser.add_argument('-b',required=True,type=str,help='Enter correct build number.')
args =parser.parse_args()

#Variables
OPT=args.t
BUILD=args.b
BRANCH=subprocess.getoutput('echo {} | cut -d "." -f 1,2,3'.format(BUILD))
CONTROLLER=os.environ.get('NS_WDIR')
UPGRADE_DIR=CONTROLLER+'/upgrade/'
DOT_REL_DIR=CONTROLLER+'/.rel/'
DB_STATUS=subprocess.getoutput('pg_isready | cut -d " " -f 3')
TEST_RUN=subprocess.getoutput('$NS_WDIR/bin/nsu_show_netstorm | grep -v "TestRun" | cut -d " " -f 1 2> /dev/null')
LOG_DIR="/tmp/BuildLogs"
TP_LOG_FILE="{}/tp_build.log".format(LOG_DIR)
NS_LOG_FILE="{}/ns_build.log".format(LOG_DIR)
ND_LOG_FILE="{}/nd_build.log".format(LOG_DIR)
CMON_LOG_FILE="{}/cmon_build.log".format(LOG_DIR)
INST_LOG_FILE="{}/installbuild.log".format(LOG_DIR)
ND_HOME="/home/cavisson/netdiagnostics"
CMON_HOME="/home/cavisson/monitors"
NS_BUILD="netstorm_all.{0}.Ubuntu1604_64.bin".format(BUILD)
TP_BUILD="thirdparty.{0}_Ubuntu1604_64.bin".format(BUILD)
ND_BUILD="netdiagnostics.{0}.tar.gz".format(BUILD)
CMON_BUILD="cmon.{0}.tar.gz".format(BUILD)
TP_URL="http://10.10.30.16:8992/U16/{0}/thirdparty.{1}_Ubuntu1604_64.bin".format(BRANCH,BUILD)
NS_URL="http://10.10.30.16:8992/U16/{0}/netstorm_all.{1}.Ubuntu1604_64.bin".format(BRANCH,BUILD)

#Making Logs Directory
subprocess.getoutput('mkdir -p {}'.format(LOG_DIR))

R_NS_BUILD_CHK=DOT_REL_DIR+NS_BUILD
R_TP_BUILD_CHK=DOT_REL_DIR+TP_BUILD
U_NS_BUILD_CHK=UPGRADE_DIR+NS_BUILD
U_TP_BUILD_CHK=UPGRADE_DIR+TP_BUILD

#Setting Up Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
file_handler = logging.FileHandler('/tmp/BuildLogs/ERROR.log')
formatter= logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def first_check():

	if DB_STATUS == 'accepting':
		if not TEST_RUN:
			return True
		else:
			logger.error("Testrun",TEST_RUN,"is running, stop session to upgrade build.")
			print("Testrun",TEST_RUN,"is running, stop session to upgrade build.")
			sys.exit(0)
	else:
		logger.error('Postgresql is not running, please start Postgresql.')
		print('Postgresql is not running, please start Postgresql.')
		sys.exit(0)


def tp_build():
	global flag
	flag=0
	start=time.time()
	subprocess.getoutput('cd {0};bash {1} > {2} 2>&1'.format(UPGRADE_DIR,TP_BUILD,TP_LOG_FILE))
	flag=1
	print()
	time.sleep(1)
	total_time_sec=time.time()-start-1
	if total_time_sec > 60:
		time_min=int(total_time_sec//60)
		time_sec=int(total_time_sec%60)
		print("Thirdparty Build Installation completed in {0}m {1}s".format(time_min,time_sec))
	else:
		print("Thirdparty Build Installation completed in {0}s".format(int(time.time()-start-1)))

def ns_build():
	global flag
	flag=0
	start=time.time()
	subprocess.getoutput('cd {0};bash {1} > {2} 2>&1'.format(UPGRADE_DIR,NS_BUILD,NS_LOG_FILE))
	flag=1
	print()
	time.sleep(1)
	total_time_sec=time.time()-start-1
	time_min=int(total_time_sec//60)
	time_sec=int(total_time_sec%60)
	print("Netstorm Build Installation completed in {0}m {1}s".format(time_min,time_sec))

def spinner():
	global flag
	#flag =0
	spinner = progress.spinner.PixelSpinner('Installing ')
	while True:
		time.sleep(1)
		spinner.next()
		if flag==1:
			sys.stdout.write("\033[F") #back to previous line
			sys.stdout.write("\033[K")
			break


def progress_thread(install):
	t1 = threading.Thread(target=install)
	t2 = threading.Thread(target=spinner)

	t2.start()
	t1.start()

	t2.join()
	t1.join()


def get_file_ownership(dir_name):
	user_owner=getpwuid(os.stat(dir_name).st_uid).pw_name,
	group_owner=getgrgid(os.stat(dir_name).st_gid).gr_name
	if (user_owner and group_owner) == 'cavisson':
		return True
	else:
		logger.error("Userowner and Groupowner of Cmon or Netdiagnostics Directory is not cavisson")
		print("Userowner and Groupowner of Cmon or Netdiagnostics Directory is not cavisson")
		sys.exit(0)



def nd_cmon_build():
	global flag
	flag=0

	start_time=time.time()
	subprocess.getoutput('cd {0};bash ./{1} --noexec > {2} 2>&1'.format(UPGRADE_DIR,NS_BUILD,NS_LOG_FILE))
	subprocess.getoutput('cd {0};cp {1} {2}'.format(UPGRADE_DIR,ND_BUILD,ND_HOME))
	subprocess.getoutput('cd {0};cp {1} {2}'.format(UPGRADE_DIR,CMON_BUILD,CMON_HOME))
	subprocess.getoutput('cd {0};tar -xvzf {1} > {2} 2>&1'.format(ND_HOME,ND_BUILD,ND_LOG_FILE))
	subprocess.getoutput('cd {0};tar -xvzf {1} > {2} 2>&1'.format(CMON_HOME,CMON_BUILD,CMON_LOG_FILE))
	flag=1
	print()
	time.sleep(1)

	print("ND and Cmon Upgraded in {:.2f}s ".format(time.time()-start_time-1))


def build_dir():
	if (path.isfile(U_TP_BUILD_CHK) and path.isfile(U_NS_BUILD_CHK)) is False:
		if path.isfile(R_TP_BUILD_CHK) and path.isfile(R_NS_BUILD_CHK):
			print('Builds are Present in .rel Directory.')
			subprocess.getoutput('mv {} {}'.format(R_TP_BUILD_CHK,UPGRADE_DIR))
			subprocess.getoutput('mv {} {}'.format(R_NS_BUILD_CHK,UPGRADE_DIR))

		elif path.isfile(R_NS_BUILD_CHK):
	        	print('Netstorm Build is Present in .rel Directory.')
	        	subprocess.getoutput('mv {} {}'.format(R_NS_BUILD_CHK,UPGRADE_DIR))
	        	print("Downloading TP build")
	        	wget.download(TP_URL,out=UPGRADE_DIR)
	    
		elif path.isfile(R_TP_BUILD_CHK):
	        	print('Thirdparty Build present in .rel Directory.')
	        	subprocess.getoutput('mv {} {}'.format(R_TP_BUILD_CHK,UPGRADE_DIR))
	        	print("Downloading NS build")
	        	wget.download(NS_URL,out=UPGRADE_DIR)        
	    	
		else:
			print("Downloading Build")
			try:
				wget.download(TP_URL,out=UPGRADE_DIR)
			except Exception as e:
				logger.error(e)
				print(e)
				sys.exit(0)

			print()
			try:
				wget.download(NS_URL,out=UPGRADE_DIR)
			except Exception as e:
				logger.error(e)
				print(e)
				sys.exit(0)

			print()
	else:
		print("Builds are present in upgrade Directory.")
	    
	subprocess.getoutput("chmod +x {0} {1}".format(NS_BUILD,TP_BUILD) )
	
	if OPT=='1':
		if first_check():
			progress_thread(tp_build)
			progress_thread(ns_build)
	elif OPT=='2':
		if get_file_ownership(CMON_HOME) and get_file_ownership(ND_HOME):
			progress_thread(nd_cmon_build)
		if first_check():
			progress_thread(tp_build)
			progress_thread(ns_build)
	        	
	elif OPT=='3':
		if get_file_ownership(CMON_HOME) and get_file_ownership(ND_HOME):
			progress_thread(nd_cmon_build)
	else: 
		print("Wrong choice")
		sys.exit(0)
	    
	
	

def main():
	build_dir()


if __name__ == '__main__':
	my_list=['"Ignorace is Bliss."', '"Time changes Everything\n -That\'s what people say. It\'s not true Doing things changes things. Not Doing things leaves things exactly as they were."', '"THINGS CHANGE\n DOESN\'t MEAN THEY GET BETTER \n you gotta make things better. You can\'t just keep talking and hoping for the best."','"Words left unsaid will sit inside your mind screaming."','"When you eliminate the impossible, Whatever remains however Improbable must be the Truth."','"Beware of False Knowledge, it is more dangerous than ignorance."', '"Wise men speak when they have something to say, Fools speak when they have to say something."','"If you\'re gonna burn bridge behind you, make sure you\'ve crossed it first."','"A friend may not always give you best advice but they do the best they can."','"It\'s your road and yours alone, Others may walk it with you, But no one can walk it for you."','"Better to embrace the hard truth than a reassuring fable. If we crave some cosmic purpose, then let us find ourselves a worthy goal."\n -Carl Sagan','"All Truths are easy to understand once they got discoverd, the point is to discover them."\n -Galileo Galilei','"When we don\'t find a logical explanation, we settle for a stupid one. Ritual is what happens when we ran out of rational."','"If Nobody hates you, you\'re doing something wrong."','"The concept you have about me won\'t change who i am, but it can change my concept about you."','"There\'s nothing in the Universe that can\'t be explained. Eventually."','"There is NO great genius without a mixture of MADNESS."\n -Aristotle','"Be a free thinker and don\'t accept everything you hear as TRUTH. Be critical and evaluate what you believe in."\n -Aristotle','"If you keep giving up on people so quickly, you\'re gonna miss out on something great."','"Whatever you do in this life, it is not legendary unless your friends are there to see it."','"The Future is scary, but you can\'t just run back to the past because it\'s familiar. Yes, it\'s tempting but it\'s a mistake."','"Listen to what the Universe is telling you to do & take the leap."','"You will be shocked when you discover how easy it is in life to part ways with people forever. That\'s why when you find someone you want to keep around, you do something about it."','"Dont\'t Judge my choices without Understanding my Reasons."','"If they\'re talking behind your back, It means that you\'re ahead of them."','"Snakes don\'t hiss anymore, they call you Babe, Bro or Friend."','"When people you don\'t even know hate you, that\'s when you know you\'re the best."','"You do what they say or they shoot you, right? Wrong! You take the gun. You pull out a bigger gun or you call their bluff or you do one of another 146 other things."','"We all make mistakes and we all pay a price."','"It takes many good deeds to build a good reputation, and only one bad one to lost it."\n -Benjamin Franklin','"Things we lost have a way of coming back to us in the end,\n If not always in the way we expect."','"Love and Happiness are nothing but Distraction."','"I began to wonder why we cuddle some animals and put a fork in others."\n -Henry Spira','"If you can fake sincerity, you can fake pretty much anything."','"The problem with people is they forget that most of the time, it\'s the small things that count."','"Take time to do what makes your soul happy."','"People never change, they just become more of who they really are."','"Hope is a good thing, maybe the Best of thing, and no good thing ever dies."','"Forget what Hurt you, But never forget what it taught you."','"Arrogance has to be earned, Tell me what have you\'ve done to earn yours."','"The world will not be destroyed by those who do evil, but by those who watch them without doint anything."\n -Alber Einstein','"If you expect the world to be fair with you because you are fair, you\'re fooling yourself. That\'s like expecting the lion not to eat you because you didn\'t eat him."','"It\'s great to have someone in your life who makes you hate yourself a little less."','"Man is the most insane species. He worships an invisible God and destroys a visible Nature. Unaware that this nature he\'s destroying is this God he\'s worshiping."\n -Hubert Reeves','"We can easily forgive a child who is afraid of the dark, The real Tragedy of life is when men are afraid of light."\n -Plato','"The problem with the world is that the intelligent people are full of doubts, while the stupid ones are full of Confidence."','"jwab tha unka bhi khamoshiyon mein\n sajishein thi unki, dil wajah bn gaya\n kahne se kaun roka h dil ko,\n koi dil se sune to karwaan bn gaya.\n -Sushil Sharma"']

	print('''
 ____        _ _     _    ___           _        _ _           
| __ ) _   _(_) | __| |  |_ _|_ __  ___| |_ __ _| | | ___ _ __ 
|  _ \| | | | | |/ _` |   | || '_ \/ __| __/ _` | | |/ _ \ '__|
| |_) | |_| | | | (_| |   | || | | \__ \ || (_| | | |  __/ |   
|____/ \__,_|_|_|\__,_|  |___|_| |_|___/\__\__,_|_|_|\___|_|   
''')
	print("Version: 1.4")
	print("Author: Kushagra225@gmail.com")
	print()
	print(random.choice(my_list))
	print()

	if len(sys.argv) > 1:
		main()
	else:
		print(""" 
 USAGE: {} -t 2 -b 4.1.14.234
         
 where
      -t for type of installation [ Default 1 ]
                        
        1 - Netstorm Build
        2 - Netstorm Build With CMON & ND Build
        3 - CMON & ND Build
                        
      -b for build version [ Value as 4.1.14.124 ]
                """.format(sys.argv[0]))

