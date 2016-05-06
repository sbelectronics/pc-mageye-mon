import Adafruit_GPIO.FT232H as FT232H
import psutil
import time

RESET=          0b00000110
WAKE=           0b00001001
UPDATE=         0b00001000
MULTIWRITE=     0b01000000
SINGLEWRITE=    0b01011000
SEQWRITE=       0b01010000
VREFWRITE=      0b10000000
GAINWRITE=      0b11000000
POWERDOWNWRITE= 0b10100000
GAINWRITE=      0b11000000

class MCP4728:
    def __init__(self, i2c):
        self.i2c = i2c
        self.values = [0,0,0,0]

    def fastwrite_all(self, v0, v1, v2, v3):
        self.values[0] = v0
        self.values[1] = v1
        self.values[2] = v2
        self.values[3] = v3
        self.fastwrite()

    def fastwrite_single(self, channel, value):
        self.values[channel] = value
        self.fastwrite()

    def fastwrite(self):
        self.i2c.writeList((self.values[0] >> 8) & 0x3F,
                                             [self.values[0] &0xFF,
                                              (self.values[1] >> 8) &0x3F,
                                              self.values[1] &0xFF,
                                              (self.values[2] >> 8) &0x3F,
                                              self.values[2] &0xFF,
                                              (self.values[3] >> 8) &0x3F,
                                              self.values[3] &0xFF])

    def set_vref(self, vr0, vr1, vr2, vr3):
        self.i2c.writeList(0b10000000 | vr0<<3 | vr1<<2 | vr2<<1 | vr3, [])

    def set_gain(self, vr0, vr1, vr2, vr3):
        self.i2c.writeList(0b11000000 | vr0<<3 | vr1<<2 | vr2<<1 | vr3, [])    

class averager:
    def __init__(self, max_values=10):
        self.max_values = max_values
        self.values = []

    def update(self, v):
        self.values.append(v)
        if len(self.values)>self.max_values:
            del self.values[0]

    def get_avg(self):
        if self.values:
            return sum(self.values)/len(self.values)
        else:
            return 0

def perfmon_loop(dac):
    averager_cpu = averager(max_values=10)

    net_values = []

    while True:
        tNow = time.time()

        # CPU utilization

        cpu = psutil.cpu_percent()
        averager_cpu.update(cpu)
        avg_cpu = averager_cpu.get_avg()
        dac.fastwrite_single(0, min(4095,int(avg_cpu*4095/100)))

        # Memory utilization

        #virtmem = psutil.virtual_memory()
        #dac.fastwrite_single(1, min(4095, int(virtmem.percent*4095/100)))

        # Network utilization

        netio = psutil.net_io_counters()
        net_bytes = netio.bytes_sent + netio.bytes_recv
        net_values.append( (net_bytes, time.time() ) )
        if len(net_values)>1:
            # compute the bytes sent between the last sample and the first sample,
            # divided by the elapsed time between the last sample and the first sample
            bps = (net_values[-1][0]-net_values[0][0]) / (net_values[-1][1]-net_values[0][1])
            if len(net_values)>10:
                # limit 10 samples = ~ 1 second
                del net_values[0]
        else:
            bps = 0

        mbps = bps/1000000

        # max out the indicator at 10 MB/s
        dac.fastwrite_single(1, min(4095, int(mbps/10.0*4095)))

        # print avg_cpu, min(4095,int(avg_cpu*4095/100)), mbps, min(4095, int(mbps/10.0*4095))

        time.sleep(0.1)

def main():
    FT232H.use_FT232H()
    ft232h = FT232H.FT232H()
    i2c = FT232H.I2CDevice(ft232h, 0x60)
    dac = MCP4728(i2c)

    dac.set_gain(0,0,0,0)
    dac.set_vref(0,0,0,0)

    dac.fastwrite_single(0, 0)
    dac.fastwrite_single(1, 0)

    #dac.fastwrite_single(0, 1024)
    #dac.fastwrite_single(1, 2048)
    #dac.fastwrite_single(2, 3072)
    #dac.fastwrite_single(3, 4095)

    perfmon_loop(dac)

if __name__ == "__main__":
    main()