# Network-Elective

To test, pls run all 4 commands in different terminals on np3@149.171.36.192 (in order):
** REPLACE msg1.txt below with any test message you want to use

1) /usr/local/bin/4123-http-server -file msg1.txt -verbose (David's Server that receive snooped message from you and verify)
2) /usr/local/bin/4123-server -port 8154 -file msg1.txt -address 149.171.36.192 -verbose (David's backdoor server)
3) python3.9 controlserver.py (Your controlserver that receives message packets snooped from snoopers/clients)
4) ./snooper (a snooper running on np3 server (i.e. ssh into np3))
5) ./snooper 149.171.36.192 (for running any snoopers not on np3 server (i.e not ssh))

# To make changes in controlserver.py:

please install filezilla and setup:
Host: sftp://149.171.36.192
Username: np3
password: vvv999

Click QuickConnect button and access folder np3, drag and drop controlserver.py across and agree to overwrite. Repeat step 1,2,3,4.
