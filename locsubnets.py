import ipaddress

def filter_subnets(input_file, output_file):
    with open(input_file, 'r') as f:
        subnet_list = [line.strip() for line in f if line.strip()]

    networks = []
    for subnet in subnet_list:
        try:
            network = ipaddress.ip_network(subnet, strict=False)
            networks.append(network)
        except ValueError as e:
            print(f"Lỗi với subnet {subnet}: {e}")
    
    networks.sort(key=lambda x: x.num_addresses, reverse=True)
    
    filtered_networks = []
    for network in networks:
        is_subset = False
        for larger_network in filtered_networks:
            if network.subnet_of(larger_network) and network != larger_network:
                is_subset = True
                break

        if not is_subset:
            if network not in filtered_networks:
                filtered_networks.append(network)
    
    with open(output_file, 'w') as f:
        for network in filtered_networks:
            f.write(f"{network}\n")
    
    print(f"Đã đọc {len(subnet_list)} subnet từ {input_file}")
    print(f"Đã lọc ra {len(filtered_networks)} subnet và ghi vào {output_file}")

if __name__ == "__main__":
    input_file = "subnets.txt"
    output_file = "filtered_subnets.txt"
    filter_subnets(input_file, output_file)