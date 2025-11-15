import xml.etree.ElementTree as ET
from Levenshtein import ratio
import itertools
import numpy as np


def determine_protocol(pdml_file):
    for event, packet in ET.iterparse(pdml_file, events=('start',)):
        if packet.tag == 'proto':
            if 'name' in packet.attrib and packet.attrib['name'] == 'tcp' :
                print(f"The protocol in {pdml_file} is based on TCP.")
                return 'TCP'
            if 'name' in packet.attrib and packet.attrib['name'] == 'udp' :
                print(f"The protocol in {pdml_file} is based on UDP.")
                return 'UDP'
    else:
        print(f"Failed to parse {pdml_file}.")

def payload_filter(file_name,port):
    port = str(port)  # modbus502

    schema_request = []
    schema_response = []
    req = False
    resp = False
    protocol = determine_protocol(file_name)
    if protocol == 'TCP':
        for event, packet in ET.iterparse(file_name, events=('start',)):
            if packet.tag == 'field':
                # print("Packet: ", packet.attrib['name']) if 'name' in packet.attrib else print("")
                if 'name' in packet.attrib and packet.attrib['name'] == 'tcp.srcport' and packet.attrib['show'] == port:
                    req = False
                    resp = True

                if 'name' in packet.attrib and packet.attrib['name'] == 'tcp.dstport' and packet.attrib['show'] == port:
                    # print("Found request packet")
                    req = True
                    resp = False


                if 'name' in packet.attrib and packet.attrib['name'] == 'tcp.payload':
                    if req:
                        schema_request.append(packet.attrib['value'])

                    elif resp:
                        schema_response.append(packet.attrib['value'])
                    req = False
                    resp = False
    if protocol == 'UDP':
        for event, packet in ET.iterparse(file_name, events=('start',)):
            if 'name' in packet.attrib and packet.attrib['name'] == 'udp.srcport' and packet.attrib['show'] == port:
                req = False
                resp = True
            if 'name' in packet.attrib and packet.attrib['name'] == 'udp.dstport' and packet.attrib['show'] == port:
                req = True
                resp = False
            if 'name' in packet.attrib and packet.attrib['name'] == 'udp.payload':
                if req:
                    schema_request.append(packet.attrib['value'])

                elif resp:

                    schema_response.append(packet.attrib['value'])
                req = False
                resp = False
    return schema_request,schema_response

#提取协功能码部分，并计算相似度分数
def LevenshteinSimilarityScore(value_list,index,step):
    # value_list=[str(item) for item in value_list]
    keyword=[]
    SimilarityScore=[]
    for el in value_list:
        keyword.append(el[index:index+step])
    combination_list = list(itertools.combinations(keyword, 2))  # 生成所有可能的两两组合列表
    for each_com in combination_list:
        SimilarityScore.append(ratio(each_com[0], each_com[1]))
    SimilarityScore = np.array(SimilarityScore)
    if len(SimilarityScore) == 0:
        return 0
    return SimilarityScore.mean()

#以十六进制形式写入txt文本
def write_list_to_file(Datalist, filename):
    # 打开（或创建）指定的文本文件
    with open(filename, 'w') as file:
        # 遍历列表中的每个元素
        for item in Datalist:
            # 将元素写入文件，每个元素占一行
            file.write(f"{item}\n")


# schema_request,schema_response=payload_filter("seeds/s7_600.pdml",102)
# write_list_to_file(schema_request, "seeds/s7_600.txt")

#calculate modbus_similarityscore
schema_request,schema_response=payload_filter("netplier_dataset/modbus_100.pdml",502)
modbus_similarityscore=LevenshteinSimilarityScore(schema_request,14,2)
print('modbus_100 keyword similarityscore:',modbus_similarityscore )
# write_list_to_file(schema_request, "Data_txt/modbus_100.txt")

# schema_request,schema_response=payload_filter("resource/modbus_500.pdml",502)
# modbus_similarityscore=LevenshteinSimilarityScore(schema_request,14,2)
# print('modbus_500 keyword similarityscore:',modbus_similarityscore )
# write_list_to_file(schema_request, "Data_txt/modbus_500.txt")


# schema_request,schema_response=payload_filter("resource/modbus_1000.pdml",502)
# modbus_similarityscore=LevenshteinSimilarityScore(schema_request,14,2)
# print('modbus_1000 keyword similarityscore:',modbus_similarityscore )
# write_list_to_file(schema_request, "Data_txt/modbus_1000.txt")

# schema_request,schema_response=payload_filter("resource/modbus_1500.pdml",502)
# modbus_similarityscore=LevenshteinSimilarityScore(schema_request,14,2)
# print('modbus_1500 keyword similarityscore:',modbus_similarityscore )
# write_list_to_file(schema_request, "Data_txt/modbus_1500.txt")

# schema_request,schema_response=payload_filter("resource/modbus_2000.pdml",502)
# modbus_similarityscore=LevenshteinSimilarityScore(schema_request,14,2)
# print('modbus_2000 keyword similarityscore:',modbus_similarityscore )
# write_list_to_file(schema_request, "Data_txt/modbus_2000.txt")

# schema_request,schema_response=payload_filter("resource/modbus_2500.pdml",502)
# modbus_similarityscore=LevenshteinSimilarityScore(schema_request,14,2)
# print('modbus_2500 keyword similarityscore:',modbus_similarityscore )
# write_list_to_file(schema_request, "Data_txt/modbus_2500.txt")

#calculate dhcp_similarityscore
# schema_request,schema_response=payload_filter("netplier_dataset/dhcp_100.pdml",67)
# dhcp_similarityscore=LevenshteinSimilarityScore(schema_request,484,2)
# print('dhcp_keyword similarityscore:',dhcp_similarityscore )
# write_list_to_file(schema_request, "Data_txt/dhcp_100.txt")

# #calculate dnp3_similarityscore
# schema_request,schema_response=payload_filter("netplier_dataset/dnp3_100.pdml",20000)
# dnp3_similarityscore=LevenshteinSimilarityScore(schema_request,24,2)
# print('dnp3_keyword similarityscore:',dnp3_similarityscore )
# write_list_to_file(schema_request, "Data_txt/dnp3_100.txt")

# schema_request,schema_response=payload_filter("netplier_dataset/ntp_100.pdml",123)
# ntp_similarityscore=LevenshteinSimilarityScore(schema_request,0,2)
# print('ntp_keyword similarityscore:',ntp_similarityscore )
# write_list_to_file(schema_request, "Data_txt/ntp_100.txt")

# schema_request,schema_response=payload_filter("netplier_dataset/tftp_100.pdml",1024)
# tftp_similarityscore=LevenshteinSimilarityScore(schema_response,0,4)
# print('tftp_keyword similarityscore:',tftp_similarityscore )
# write_list_to_file(schema_response, "Data_txt/tftp_100.txt")

# schema_request,schema_response=payload_filter("netplier_dataset/s7_100.pdml",102)
# s7_similarityscore=LevenshteinSimilarityScore(schema_request,34,2)
# print('s7_keyword similarityscore:',s7_similarityscore )
# write_list_to_file(schema_request, "Data_txt/s7_100.txt")