from pytapo import Tapo

user = "cepy01.2026@gmail.com" # user you set in Advanced Settings -> Camera Account
password = "Castelar2026" # password you set in Advanced Settings -> Camera Account
host = "192.168.60.60" # ip of the camera, example: 192.168.1.52

tapo = Tapo(host, user, password)

print(tapo.getBasicInfo())