
from polyglot.detect import Detector
# pip3 install pyicu
# pip3 install pycld2
# pip3 install morfessor


text = "Bonjour le monde!"
detector = Detector(text)
language = detector.language.code
print(language)