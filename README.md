# Network-Elective

To test, pls run all 4 commands in different terminals on np3@149.171.36.192 (in order):
1) /usr/local/bin/4123-http-server -file msg1.txt -verbose
2) /usr/local/bin/4123-server -port 8154 -file msg1.txt -address 149.171.36.192 -verbose
3) python3.9 controlserver.py
4) ./snooper

To make changes in controlserver.py -> time.sleep(x) statement:
please install filezilla and setup:
Host: sftp://149.171.36.192
Username: np3
password: vvv999

Click QuickConnect button and access folder np3, drag and drop controlserver.py across and agree to overwrite. Repeat step 1,2,3,4.
