import requests
import json
import os
import io
import zipfile
import time
import numpy as np
import ipaddress
#import arpreq
from getmac import get_mac_address


class UltimakerError(Exception):
    """Base error for ulimaker class.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class Ultimaker:   
    # @param ip: IP address of the printer   
    # @param application: name of the application in string form, used during authentication requests and is shown on the printer.   
    #def __init__(self, subnet, mac, application, auth_filename):
    def __init__(self, application, config):
        self.load_config(config)

        if self.use_static_ip:
            self.set_printer_ip(self.printer_ip)
        else:
            printer_ip = self.get_ip_from_mac()
            if printer_ip is None:
                raise UltimakerError("Ultimaker: Could not find printer IP")
            self.set_printer_ip(printer_ip)

        self.__application = application
        self.__session = requests.sessions.Session()       
 
        if not self.__check_auth():
            raise UltimakerError("Ultimaker: Authentication Failed")

    def load_config(self, config):
        self.use_static_ip = config.STATIC_IP
        self.printer_mac = config.PRINTER_MAC
        self.printer_subnet = config.PRINTER_SUBNET
        self.printer_ip = config.PRINTER_IP
        
        ultimaker_id = config.ULTIMAKER_ID
        ultimaker_key = config.ULTIMAKER_KEY

        self.__set_auth_data(ultimaker_id, ultimaker_key)   
   
    # Set new authentication data, authentication data is send with each HTTP request to make sure we can PUT/POST data.   
    def __set_auth_data(self, id, key):       
        self.__auth_id = id       
        self.__auth_key = key       
        self.__auth = requests.auth.HTTPDigestAuth(self.__auth_id, self.__auth_key)   

    # Get printer ip from mac. Return None if not found.
    def get_ip_from_mac(self):
        for ip in ipaddress.IPv4Network(self.printer_subnet):
            # try without network request
            mac = get_mac_address(ip=str(ip))
            # if we dont get mac from arp table try updating mac
            if mac == '00:00:00:00:00:00':
                mac = get_mac_address(ip=str(ip), network_request=True)
            # if we dont get mac from arp table again, it probably was
            if mac == '00:00:00:00:00:00':
                mac = get_mac_address(ip=str(ip), network_request=True)

            if mac is not None and mac.lower() == self.printer_mac.lower():
                print ('host: ' + str(ip) + ', mac: ' + mac)
                return str(ip)
        return None

    # Set printer ip
    def set_printer_ip(self, ip):
        self.__ip = ip

    # Reset printer IP from mac. Return True if success, False otherwise.
    def reset_printer_ip(self):
        ip = self.get_ip_from_mac()
        if ip is not None:
            self.set_printer_ip(ip)
            return True
        return False  

    # Check if our authentication is valid, and if it is not request a new ID/KEY combination, 
    #this function can block till the user selected ALLOW/DENY on the printer.   
    def __check_auth(self):
        response = self.get("api/v1/auth/verify")
        if response.status_code == 200:
            return True
        return False

    # Do a new HTTP request to the printer. It formats data as JSON, and fills in the IP part of the URL.   
    def request(self, method, path, **kwargs):       
        if "data" in kwargs:           
            kwargs["data"] = json.dumps(kwargs["data"])           
        if "headers" not in kwargs:               
            kwargs["headers"] = {"Content-type": "application/json"}     
        try:
            response = self.__session.request(method, "http://{}/{}".format(self.__ip, path), auth=self.__auth, **kwargs)
        except requests.exceptions.ConnectionError:
            if self.use_static_ip:
                # try to find new ip
                if self.reset_printer_ip():
                    # try with new ip
                    response = self.__session.request(method, "http://{}/{}".format(self.__ip, path), auth=self.__auth, **kwargs)
                else:
                    # ip not found
                    raise UltimakerError('Ultimaker: Could not get printer IP')
            else:
                raise UltimakerError('Ultimaker: Could not connect to printer at {}'.format(self.__ip))
        return response

    # Shorthand function to do a "GET" request.   
    def get(self, path, **kwargs):       
        return self.request("get", path, **kwargs)   

    # Shorthand function to do a "PUT" request.   
    def put(self, path, **kwargs):       
        return self.request("put", path, **kwargs)   

    # Shorthand function to do a "POST" request.   
    def post(self, path, **kwargs):       
        return self.request("post", path, **kwargs)

    def get_printer_status(self):
        response = self.get('api/v1/printer')
        res = { 'status_code': response.status_code }

        if response.status_code == 200:
            status_json = response.json()

            res['status'] = status_json['status']
            res['bed_temp_cur'] = status_json['bed']['temperature']['current']
            res['bed_temp_target'] = status_json['bed']['temperature']['target']

            res['ext_1_temp_cur'] = status_json['heads'][0]['extruders'][0]['hotend']['temperature']['current']
            res['ext_1_temp_target'] = status_json['heads'][0]['extruders'][0]['hotend']['temperature']['target']
            res['ext_1_feeder_max_speed'] = status_json['heads'][0]['extruders'][0]['feeder']['max_speed']
        
        return res

    def get_printjob_status(self):
        response = self.get('api/v1/print_job')

        res = { 'status_code': response.status_code }

        if response.status_code == 200:
            status_json = response.json()
        
            res['status'] = status_json['state']
            res['time_total'] = status_json['time_total']
            res['time_elapsed'] = status_json['time_elapsed']
            res['print_name'] = status_json['name']
            res['progress'] = status_json['progress']
            res['datetime_started'] = status_json['datetime_started']
            res['datetime_finished'] = status_json['datetime_finished']
            res['pause_source'] = status_json['pause_source']

        return res

    def get_printer_state(self):
        response = self.get('api/v1/printer/status')

        res = { 'status_code': response.status_code }
        if response.status_code == 200:
            res['printer_status'] = response.json()

            if res['printer_status'] == 'printing':
                result = self.get_printjob_state()
                res['printjob_state'] = result['printjob_state']
                if result['printjob_state'] == 'paused':
                    pause_source_result = self.get_printjob_pause_source()
                    res['pause_source'] = pause_source_result['pause_source']
            else:
                res['printjob_state'] = 'no_printjob'

        return res 

    def get_printjob_state(self):
        response = self.get('api/v1/print_job/state')

        res = { 'status_code': response.status_code }
        if response.status_code == 200:
            res['printjob_state'] = response.json()
        else:
            res['printjob_state'] = 'no_printjob'

        return res 

    def get_printjob_pause_source(self):
        response = self.get('api/v1/print_job/pause_source')

        res = { 'status_code': response.status_code }
        if response.status_code == 200:
            res['pause_source'] = response.json()
        else:
            res['pause_source'] = ''

        return res 

    def get_printer_image(self):
        stream = self.__session.get("http://{}:8080/?action=stream".format(self.__ip), stream=True)
        read_bytes = bytes()

        for chunk in stream.iter_content(chunk_size=1024):
            read_bytes += chunk
            jpg_start = read_bytes.find(b'\xff\xd8')
            jpg_end = read_bytes.find(b'\xff\xd9')

            if jpg_start != -1 and jpg_end != -1:
                jpg = read_bytes[jpg_start:jpg_end+2]
                img_np = np.frombuffer(jpg, dtype=np.uint8)
                bio = io.BytesIO(img_np)
                bio.seek(0)
                return bio 
    
    def get_camera_snapshot(self):
        #response = self.get('camera/0/snapshot', stream=True)
        response = self.__session.get("http://{}:8080/?action=snapshot".format(self.__ip), stream=True)
        bio = io.BytesIO(response.content)
        bio.seek(0)
        return bio

    def get_led_brightness(self):
        response = self.get('api/v1/printer/led/brightness')

        res = {}
        res['status_code'] = response.status_code

        if res['status_code'] == 200:
            res['level'] = response.json()

        return res           

    def set_led_brightness(self, brightness):
        response = self.put('api/v1/printer/led/brightness', data=brightness)

        res = response.json()
        res['status_code'] = response.status_code

        return res

    def pause_printjob(self):
        response = self.put('api/v1/print_job/state', data={'target': 'pause'})

        res = response.json()
        res['status_code'] = response.status_code

        return res

    def unpause_printjob(self):
        response = self.put('api/v1/print_job/state', data={'target': 'print'})

        res = response.json()
        res['status_code'] = response.status_code

        return res

    def print_model(self, name, path):
        # api.post("api/v1/print_job", files={"file": ("UM3_Box_20x20x10.gcode", open("UM3_Box_20x20x10.gcode", "rb"))})
        #with open(path, 'rb') as f:
        response = self.post('api/v1/print_job', files={"file": (name, open(path, 'rb'))})

        return response

    def get_printjob_container(self):
        response = self.get('api/v1/print_job/container')

        return response

    def get_printjob_thumbnail(self):
        response = self.get_printjob_container()
        result = { 'status_code': response.status_code }
        #open('test_container', 'wb').write(result.content)
        if response.status_code == 200:
            container_file = io.BytesIO(response.content)
            container_file.seek(0)
            if zipfile.is_zipfile(container_file):
                zf = zipfile.ZipFile(container_file, "r")
                thumbnail = zf.open('/Metadata/thumbnail.png').read()
                zf.close()
                result['has_thumbnail'] = True
                thumbnail = io.BytesIO(thumbnail)
                thumbnail.seek(0)
                result['thumbnail'] = thumbnail
            else:
                result['has_thumbnail'] = False

        return result


if __name__ == '__main__':
    try:
        #ultimaker = Ultimaker("10.1.196.0/22", "cc:bd:d3:00:71:2e", "TelegramBot", "ultimker_auth_file.json")

        #ultimaker = Ultimaker("10.1.196.0/22", "cc:bd:d3:00:71:2e", "TelegramBot", "ultimker_auth_file.json")
        #print(ultimaker.get_printer_status().json())
        #print(ultimaker.get_printjob_status()['status_code'])
        #print(ultimaker.get_led_brightness())
        #print(ultimaker.get_camera_snapshot().raw.__dict__)
        # image_data = ultimaker.get_camera_snapshot()
        # # print (image_data.content)

        # # image_data.raw.decode_content = True
        # # print (image_data.raw.seekable())
        # # print(image_data.raw.tell())
        # # print (image_data.raw.read())

        # from PIL import Image
        # image = Image.open(io.BytesIO(image_data.content))

        # import matplotlib.pyplot as plt
        # # image = Image.open(image_data)
        # # image.seek(0)
        # plt.imshow(np.asarray(image))
        # plt.show()

        #r = ultimaker.get('camera/0/snapshot', stream=True, allow_redirects=False)
        #print(r.headers)

        # r = ultimaker.print_model('UMS5_plastic_underactuated_finger_phalanx_1(1).ufp', 'UMS5_plastic_underactuated_finger_phalanx_1(1).ufp')
        # print (r)
        # print (r.json())


        # f = 'UMS5_plastic_underactuated_finger_phalanx_1(1).ufp'
        # result = ultimaker.post("api/v1/print_job", files={"file": (f, open(f, "rb"))})
        # print (result)
        # print (result.json())

        # with open(f, "rb") as fl:
        #     with open('test.ufp', 'wb') as fl2:
        #         fl2.write(fl.read())

        #result = ultimaker.get_printjob_container()
        #open('test_container', 'wb').write(result.content)
        # result_file = io.BytesIO(result.content)
        # result_file.seek(0)
        # #result = ultimaker.get('api/v1/print_job/gcode')
        # print(zipfile.is_zipfile(result_file))
        # zf = zipfile.ZipFile(result_file, "r")
        # f = zf.open('/Metadata/thumbnail.png')
        # fl = f.read()
        # zf.close()
        # print(type(fl))
        # #/Metadata/thumbnail.png'
        # open('thumbnail.png', 'wb').write(fl)

        #print(ultimaker.get_led_brightness())
        pass
    except requests.exceptions.ConnectionError as ce:
        print ('connection error')
