import xml.etree.ElementTree as ET
tree = ET.parse('brainspell2.xml')
root = tree.getroot()

def convertToJSON(xmlObj):
    p = {}
    for attr in xmlObj:
        if len(attr) != 0:
            if attr.tag.lower() in p:
                if not isinstance(p[attr.tag.lower()], list):
                    value = p[attr.tag.lower()]
                    p[attr.tag.lower()] = [value]
                p[attr.tag.lower()].append(convertToJSON(attr))
            else:
                p[attr.tag.lower()] = convertToJSON(attr)
        else:
            if attr.text is not None:
                attr.text = attr.text.replace("\n", "").replace("\t", "")
            if attr.tag.lower() in p:
                if not isinstance(p[attr.tag.lower()], list):
                    value = p[attr.tag.lower()]
                    p[attr.tag.lower()] = [value]
                p[attr.tag.lower()].append(attr.text)
            else:
                p[attr.tag.lower()] = attr.text
    return p

print(convertToJSON(root))