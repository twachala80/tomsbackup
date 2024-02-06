#!/usr/bin/env python

# A simple script for creating backups.
# 1) Reads a config from 'tomsbackup.ini' file.
# 2) Creates tar archives in the the subdirectories with the names containing time of the backup.
# 3) Single tar archive contains the files from each directory from the list.
# 4) Prunes existing backups leaving only last N backups.
#
# All suggestions how to improve the script are welcome. 
# Please feel free to send them to: Tomasz.Wachala@ifj.edu.pl
#
# Created from scratch: June 2010
# Added pruning: July 2010
# Added configparser support: 2018
#
# TODO LIST: backup via ssh, mysql backup

import os, sys, os.path, shutil, socket, re, glob, time, stat, configparser
from datetime import datetime

print("===============================================================================") 
print("                         TOMSBACKUP backup script")
print("===============================================================================")

###############################################################
#Function to prompt user for y/n choice
def yn_choice(message, default='y'):
    choices = 'Y/n' if default.lower() in ('y', 'yes') else 'y/N'
    choice = input("%s (%s) " % (message, choices))
    values = ('y', 'yes', '') if default == 'y' else ('y', 'yes')
    return True if choice.strip().lower() in values else False 

###############################################################
#Function to get directory size
def get_size(path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            #print("# %s" % f)
            #if os.path.exists(f):
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                #print("# %s" % fp)
                total_size += os.path.getsize(fp)
    total_size = total_size >> 20

    return total_size   # in megabytes
###############################################################
#Check if we have sufficient number of command line parameters
#if len(sys.argv) <= 1:
#    print("USAGE:\n%s [backup_directory]" % sys.argv[0])
#    print(" backup_directory - destination directory for the backup files")
#    sys.exit(1)
###############################################################
# Init config parser
config = configparser.ConfigParser()
config.read("tomsbackup.ini")
#
# Now, read the config file
#
#Paths
if "DestinationDir" in config["Paths"]:
    backupdir = config.get("Paths",'DestinationDir')
if "DirectoriesToBackup" in config["Paths"]:
    directoriesToBackup = config.get("Paths",'DirectoriesToBackup').split()
#print("DirectoriesToBackup=%s" % directoriesToBackup)
#
# Backup Ubuntu's list of installed packages:
if "BackupUbuntuListOfPackages" in config["General"]:
    BackupUbuntuListOfPackages = config.getboolean("General","BackupUbuntuListOfPackages")
#
# Backup Firefox bookmarks
if "BackupFirefoxProfile" in config["General"]:
    BackupFirefoxProfile = config.getboolean("General","BackupFirefoxProfile")
#Pruning
if "Prune" in config["General"]:
    prune = config.getboolean("General", "Prune")
#Summary
if "GZipSummary" in config["General"]:
    gzipSummary = config.getboolean("General","GzipSummary")
#Pruning
if "NumberOfBackupsToKeep" in config["Pruning"]:
    NumberOfBackupsToKeep = config.getint("Pruning","NumberOfBackupsToKeep")
###############################################################
# Sanity checks for backup directory...
###############################################################
if not os.path.exists(backupdir):
    print("ERROR: Missing: %s directory!" % backupdir)
    sys.exit(1)    
if not os.path.isdir(backupdir):
    print("ERROR: %s is not a directory!" % backupdir)
    sys.exit(1)
if not os.access(backupdir,os.R_OK):
    print("ERROR: Cannot read %s directory!" % backupdir)
    sys.exit(1)
if not os.access(backupdir,os.W_OK):
    print("ERROR: No write permissions for %s directory!" % backupdir)
    sys.exit(1)
##############################################################
# Prepare directories
##############################################################
#
#Get the current date and time
t = datetime.now()
timestamp = t.strftime("%Y%m%d_%H%M%S")
timetoprint = t.strftime("%Y.%m.%d %H:%M:%S")

#Get the host name
hostname = socket.gethostname()
hostname.replace(".","_")

#Change current directory to the destination dir
os.chdir(backupdir)

#Create subdirectory with the date,time and hostname in it's name
currdir = timestamp + "_" + hostname
os.mkdir(currdir)

#Change current working directory to the subdirectory
os.chdir(currdir)

#Define summary file
summaryname = currdir + "_backup_summary.txt"
##############################################################
# Loop over directories and copy them using rsync
##############################################################
#
print(">>>> Current time: %s" % timetoprint)
print(">>>> Preparing backup (Please be patient. Estimating the size of the backup may take a while...)")

nDirsToBackup = len(directoriesToBackup)

#Print the size of the backup
backupSize=0
for directory in directoriesToBackup:
    dirSize = get_size(directory)
    print(">> Directory: %s with size: %i MB" % (directory,dirSize))
    backupSize = backupSize + dirSize
   
print(">> Total size of the backup: %i MB" % backupSize)
print(">> Total space available in destination directory:")
os.system("df -h %s" % backupdir)
   
if not yn_choice("Do you want to continue?"):    
    sys.exit(0);

#Loop over directories and backup them
for directory in directoriesToBackup: 
    print(">> Creating backup of the directory: %s" % directory)

    #Check if we can access this directory
    if not os.path.exists(directory):
        print("\nERROR: Missing %s directory! Skipping..." % directory)
        #sys.exit(1)
        continue
    
    if not os.path.isdir(directory):
        print("\nERROR: %s is not a directory! Skipping..." % directory )
        #sys.exit(1)
        continue

    if not os.access(directory,os.R_OK):
        print("\nERROR: Cannot read %s directory! Skipping" % directory)
        #sys.exit(1)
        continue
    
    #Replace all '/' with '_' in the path of the directory which we want to backup
    #tartarget = directory.replace("/","_") + ".tgz"
    tartarget = directory.replace("/","_")
   
    #print tartarget
    #print directory
    
    #Run tar cvzf on this directory and append the result to the summary file
    #status = os.system("tar cvzf %s --exclude=*.tmp --exclude=tmp --exclude=lost+found --exclude=*cache --exclude=*Trash %s >> %s 2>&1" % (tartarget,directory,summaryname))
    status = os.system("rsync -avz --progress --exclude=*.tmp --exclude=tmp --exclude=lost+found --exclude=*cache --exclude=*Trash %s %s | tee -a %s" % (directory,tartarget,summaryname))
    #if status != 0:
        #print "\nERROR: Cannot execute tar cvzf on " + directory + "!"    
        #sys.exit(status)

    if gzipSummary:
        #Compress summary file	
        status = os.system("gzip -f %s" % (summaryname))
        if status != 0:
            print("\nERROR: Cannot execute gzip on %s !" % summaryname)
            sys.exit(status)

    #This is here for remote copying ...
    #rsync -avzh --stats --progress remoteuser@remoteip  localpath 
	
    print(">> Done!")
###########################################################
# Ubuntu list of packages
if BackupUbuntuListOfPackages:
    print(">> Creating backup of the list of installed packages, keys, repos...")
    os.mkdir("UbuntuListOfInstalledPackages")

    #Now backup the list of installed packages, keys and repos
    status = os.system("dpkg --get-selections > UbuntuListOfInstalledPackages/Package.list")
    if status != 0:
        print("\nERROR: Cannot execute dpkg --get-selections > UbuntuListOfInstalledPackages/Package.list")
        sys.exit(status)
    
    status = os.system("sudo rsync -avz /etc/apt/sources.list* UbuntuListOfInstalledPackages")
    if status != 0:
        print("\nERROR: Cannot execute sudo rsync -avz /etc/apt/sources.list* UbuntuListOfInstalledPackages")
        sys.exit(status)

    status = os.system("sudo apt-key exportall > UbuntuListOfInstalledPackages/Repo.keys")
    if status != 0:
        print("\nERROR: Cannot execute sudo apt-key exportall > UbuntuListOfInstalledPackages/Repo.keys")
        sys.exit(status)
    
    print(">> Done!")
##########################################################
# Firefox profile backup
if BackupFirefoxProfile:
    print(">> Creating backup of the Firefox profile...")
    os.mkdir("FirefoxProfile")

    #Now backup Firefox default profile (IMPORTANT: You have to switch browser.bookmarks.autoExportHTML to true in Firefox)
    status = os.system("rsync -avz ~/.mozilla/firefox/*.default FirefoxProfile")
    if status != 0:
        print("\nERROR: Cannot execute rsync -avz ~/.mozilla/firefox/*.default FirefoxProfile")
        sys.exit(status)

    print(">> Done!")
##########################################################
#Finito
print(">>>> Everything backed up SUCCESSFULLY!")
################################################################
# Prune older backups leaving only 3 latest
################################################################
if prune: 
    print(">>>> Pruning old backups")

    if not yn_choice("Do you want to prune old backups? NOTE: You must have permissions to delete the files!"):
        print("===============================================================================\n" + "                        END OF backup script\n" + "===============================================================================")
        sys.exit(0);

    # Directory containing all backups
    root = backupdir

    # List of backups (subdirectories)
    date_file_list = []

    # Loop over   
    for folder in glob.glob(root):
 
        # Select all subdirs
        for file in glob.glob(folder + '/*'):
 
            # retrieves the stats for the current file as a tuple
            # (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime)
            # the tuple element mtime at index 8 is the last-modified-date
            file_stats = os.stat(file)
 
 	    #Check if it's a directory
            if stat.S_ISDIR(file_stats[stat.ST_MODE]):              
	        # create tuple (year yyyy, month(1-12), day(1-31), hour(0-23), minute(0-59), second(0-59),
                # weekday(0-6, 0 is monday), Julian day(1-366), daylight flag(-1,0 or 1)) from seconds since epoch
                # note: this tuple can be sorted properly by date and time
                lastmod_date = time.localtime(file_stats[8])
      
                # create list of tuples ready for sorting by date
                date_file_tuple = lastmod_date, file
                date_file_list.append(date_file_tuple)
       
    #Print date_file_list
    date_file_list.sort()
    #Reverse to have the newest firs
    date_file_list.reverse()

    print(">> List of existing backups:")
    print("\n%-40s %-40s %s" % ("Name:", "Last modified:", "Status:"))
 
    for file in date_file_list:
        # extract just the filename      
        folder, file_name = os.path.split(file[1])
      
        # convert date tuple to MM/DD/YYYY HH:MM:SS format
        file_date = time.strftime("%m/%d/%y %H:%M:%S", file[0])
        print("%-40s %-40s" % (file_name, file_date))
        if date_file_list.index(file) > NumberOfBackupsToKeep-1:
            if not yn_choice("Deleting backup directory %s. Is it ok?" % file_name):
                continue

            try:
                shutil.rmtree(file[1]) 
            except OSError as e:
                print(e)
                raise
                continue
        else:
            print("OK")
    
    print(">>>> Pruning DONE!")
    print("===============================================================================\n" + "                        END OF backup script\n" + "===============================================================================")
