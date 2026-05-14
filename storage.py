
def append_to_file(file_path, field_type, index, step):
    new_entry = f"{field_type}[{index}, {step}]"
    with open(file_path, 'a', encoding='utf-8') as file:
        file.write(new_entry + '\n')

def generate_new_entry():
    new_field_type = '请求关键字段'
    new_index = 7
    new_step = 15
    return new_field_type, new_index, new_step

def parse_txt_file(file_path):
    constant_fields = []
    request_key_fields = []
    response_key_fields = []

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if line.startswith('不变字段'):
                data = line.strip('不变字段[]')
                index, step = map(int, data.split(', '))
                constant_fields.append((index, step))
            elif line.startswith('请求关键字段'):
                data = line.strip('请求关键字段[]')
                index, step = map(int, data.split(', '))
                request_key_fields.append((index, step))
            elif line.startswith('响应关键字段'):
                data = line.strip('响应关键字段[]')
                index, step = map(int, data.split(', '))
                response_key_fields.append((index, step))
    return constant_fields, request_key_fields, response_key_fields


def get_constant_fields(file_path):
    constant_fields, _, _ = parse_txt_file(file_path)
    return constant_fields


def get_request_key_fields(file_path):
    _, request_key_fields, _ = parse_txt_file(file_path)
    return request_key_fields


def get_response_key_fields(file_path):
    _, _, response_key_fields = parse_txt_file(file_path)
    return response_key_fields


def main():
    file_path = 'Protocol format.txt'

    constant_fields = get_constant_fields(file_path)
    request_key_fields = get_request_key_fields(file_path)
    response_key_fields = get_response_key_fields(file_path)

    print("不变字段: ", constant_fields)
    print("请求关键字段: ", request_key_fields)
    print("响应关键字段: ", response_key_fields)
    # print(type(constant_fields))
    # print(response_key_fields[0])
    # print(response_key_fields[0][0])
if __name__ == "__main__":
    main()