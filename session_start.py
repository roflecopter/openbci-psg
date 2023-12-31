import os, time, datetime, sys, re, pty, serial
import sqlite3, json
from contextlib import closing
import pyOpenBCI

# config
working_dir = '/path/to/openbci-psg' 
ch_n = 8 # cyton without daisy have channels
channels = {'F7-T3':0,'F8-T3':1,'O2-T3':2} # for sd processing at the session end, Label:%N [0-7] 
gain = 24 # gain for all channels: 1 2 4 6 12 24
sampling_rate = 250 # 250 500 1000 ...
duration = '24H' # 5M 12H 24H ...

t_sleep = 1
dbg = False
board = pyOpenBCI.OpenBCICyton(port='/dev/cu.usbserial-D200PMQM', daisy=False)
time.sleep(t_sleep)
res = board.ser.read_all().decode()
res
if dbg:
    board.write_command('?')
    time.sleep(t_sleep * 3)
    registers = board.ser.read_all().decode()
    registers2 = board.ser.read_all().decode()
    # print(registers + registers2)

def print_raw(sample):
    print(sample.channels_data)

# command list is here https://docs.openbci.com/Cyton/CytonSDK/
# check if board in default mode

board.write_command('//')
time.sleep(t_sleep)
res = board.ser.read_all().decode()
if dbg: print(res)
if res == 'Success: default$$$':
    print(f'mode is default')
else:
    sys.exit(f'mode is not default')

# set sampling rate
sampling_rates = {16000:0,8000:1,4000:2,2000:3,1000:4,500:5,250:6}
board.write_command('~' + str(sampling_rates[sampling_rate]))
time.sleep(t_sleep)
res = board.ser.read_all().decode()
if dbg: print(res)
if len(re.findall('Sample rate is ' + str(sampling_rate) + 'Hz', res)) > 0:
    print(f'sampling rate set to {sampling_rate}')
else:
    sys.exit(f'sampling rate not set')

# channel configuration
gains = {1:0,2:1,4:2,6:3,8:4,12:5,24:6}
on = '0' + str(gains[gain]) + '0110X'; off = '160000X'
chs = [on] * len(channels) + [off] * (ch_n -len(channels))
ch_cmd = ('x1' + chs[0] + 'x2' + chs[1] + 
    'x3' + chs[2] + 'x4' + chs[3] + 
    'x5' + chs[4]+ 'x6' + chs[5] + 
    'x7' + chs[6] + 'x8' + chs[7])
print(ch_cmd)
board.write_command(ch_cmd)
time.sleep(t_sleep*5)
res = board.ser.read_all().decode()
if dbg: print(res)
if (len(re.findall('Success', res)) > 0):
    print(f'channels set')
else:
    sys.exit(f'channels not set')

if dbg: 
    board.write_command('?')
    time.sleep(t_sleep*3)
    new_registers = board.ser.read_all().decode()
    new_registers2 = board.ser.read_all().decode()
    # print(new_registers + registers2)

# enable sdcard writing
durations = {'5M':'A','12H':'K','24H':'L'}
board.write_command(durations[duration])
time.sleep(t_sleep * 5)

res = board.ser.read_all().decode()
if dbg: print(res)
if len(re.findall('correct', res)) > 0:
    re_file = re.findall(r'OBCI\_.*\.TXT', res)
    if len(re_file) > 0:
        print(f'SD file init success {re_file}')
        sd_file = re_file[0]
        # board.start_stream(print_raw)
        board.write_command('~~')
        time.sleep(t_sleep)
        res = board.ser.read_all().decode()
        print(res)
        board.write_command('b')
        dts = datetime.datetime.now()
        print(f'Session started at {dts}')
        time.sleep(t_sleep)
        with closing(sqlite3.connect(os.path.join(working_dir, 'data','sessions.db'), timeout=10)) as con:
            with con:
                with closing(con.cursor()) as cur:
                    sql = 'CREATE TABLE IF NOT EXISTS Sessions(dts datetime NOT NULL PRIMARY KEY, file VARCHAR(256), settings TEXT NOT NULL)'
                    cur.execute(sql)
                    settings = {'gain':gain, 'channels':channels, 'sf': sampling_rate}
                    json_settings = json.dumps(settings)
                    sql = 'REPLACE INTO Sessions (dts,file,settings) VALUES (\'' + dts.strftime('%Y-%m-%d %H:%M:%S') + '\', \'' + sd_file + '\', \'' + json_settings + '\')'
                    cur.execute(sql)
            
                    # sql = 'SELECT * FROM Sessions'
                    # cur.execute(sql)
                    # cur.fetchall()

else:
    sys.exit(f'SD init failed')
    
# dte = datetime.datetime.now(); print(dte)
