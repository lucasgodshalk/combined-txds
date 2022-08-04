import os
import re
import subprocess

data_dir = os.path.dirname(__file__)

voltdump_regex = r"object\svoltdump\s\{[\n\r\s]+filename\s[a-zA-Z]+\.csv;[\n\r\s]+mode\sRECT;[\n\r\s]+\}"

clock_regex = r"clock\s*{"

dumpstr = """


object voltdump {
     filename result.csv;
     mode RECT;
}
"""

clockstr = """


clock {
	timezone EST+8EDT;
	timestamp '2000-01-01 0:00:00';
	stoptime '2000-01-01 0:00:01';
}
"""

for dirpath, dirnames, filenames in os.walk(data_dir):
    
    for filename in filenames:
        if not filename.endswith(".glm"):
            continue

        casefile = os.path.join(dirpath, filename)

        if not casefile.endswith("node.glm"):
            desiredcasefile = os.path.join(dirpath, "node.glm")
            os.rename(casefile, desiredcasefile)
            casefile = desiredcasefile

        with open(casefile, 'r+') as file:
            filestr = file.read()

            if re.search(voltdump_regex, filestr) == None:
                file.write(dumpstr)
            if re.search(clock_regex, filestr) == None:
                file.write(clockstr)
        
        print(f"Executing case {casefile}")
        subprocess.run(["gridlabd.exe", "node.glm"], cwd=dirpath)

