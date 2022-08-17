import os
import re
import subprocess
import shutil
from pathlib import Path

###
#First we need to copy the taxonomy feeders over to our three_phase folder
###

three_phase_dir = os.path.join(os.path.dirname(__file__), "three_phase")

taxonomy_dir = os.path.join(os.path.dirname(__file__), "Taxonomy_Feeders")

for object in os.listdir(taxonomy_dir):
    existingcasefile = os.path.join(taxonomy_dir, object)

    if not os.path.isfile(existingcasefile):
        continue
    
    filename = object

    if not filename.endswith(".glm"):
        continue

    newcasename = filename.replace(".glm", "").replace(".", "_").replace("-", "_").lower()

    newcasedir = os.path.join(three_phase_dir, newcasename)

    Path(newcasedir).mkdir(parents=True, exist_ok=True)

    newcasefile = os.path.join(newcasedir, "node.glm")

    shutil.copyfile(existingcasefile, newcasefile)
    

###
#Then we normalize glm files
###


voltdump_regex = r"object\svoltdump\s*\{[^//]*?\};?"

dumpstr = """object voltdump {
     filename result.csv;
     mode RECT;
}"""

clock_regex = r"clock\s*\{[^//]*?\};?"

clockstr = """clock {
	timezone EST+8EDT;
	timestamp '2000-01-01 0:00:00';
	stoptime '2000-01-01 0:00:01';
}"""

tape_regex = r"module tape;"

gridlab_targets = []

for dirpath, dirnames, filenames in os.walk(three_phase_dir):
    
    for filename in filenames:
        if not filename.endswith(".glm"):
            continue

        existingcasefile = os.path.join(dirpath, filename)

        if not existingcasefile.endswith("node.glm"):
            desiredcasefile = os.path.join(dirpath, "node.glm")
            os.rename(existingcasefile, desiredcasefile)
            existingcasefile = desiredcasefile

        with open(existingcasefile, 'r') as file:
            filestr = file.read()

        with open(existingcasefile, 'w') as file:

            filestr = re.sub(voltdump_regex, dumpstr, filestr)
            filestr = re.sub(clock_regex, clockstr, filestr)

            #Tape generates a bunch of extra files we don't want.
            filestr = filestr.replace("module tape;", "")

            if re.search(voltdump_regex, filestr) == None:
                filestr += os.linesep + os.linesep + dumpstr
            if re.search(clock_regex, filestr) == None:
                filestr += os.linesep + os.linesep + clockstr

            file.write(filestr)
        

        gridlab_targets.append((existingcasefile, dirpath))

###
#Finally we execute each one with gridlabd.
###

for (existingcasefile, dirpath) in gridlab_targets:
    print(f"Executing case {existingcasefile}")
    subprocess.run(["gridlabd.exe", "node.glm"], cwd=dirpath)