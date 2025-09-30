#!/usr/bin/env python3
"""
super_loadtest_input.py

Async + aiohttp multiprocess load tester
Phiên bản bỏ uvloop (chạy được ngay trên Termux).
Nhập thông số trực tiếp (URL, thời gian, RPS, concurrency, processes, method mix).
"""

import asyncio, aiohttp, time, random, string, multiprocessing as mp
from statistics import mean, median

# ---------- Payload ----------
def random_string(n=20):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))

def gen_payload(payload_type="json", size=512):
    if payload_type == "json":
        return {"data": random_string(size)}
    elif payload_type == "form":
        return {"field": random_string(size)}
    elif payload_type == "binary":
        return random_string(size).encode()
    return None

# ---------- Async Worker ----------
async def worker(url, methods, weights, rps, duration, concurrency, q):
    sem = asyncio.Semaphore(concurrency)
    timeout = aiohttp.ClientTimeout(total=10)
    connector = aiohttp.TCPConnector(limit=concurrency, ssl=False)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        end_time = time.time() + duration
        interval = 1.0 / rps if rps > 0 else 0
        results = []

        while time.time() < end_time:
            await sem.acquire()
            async def do_req():
                try:
                    method = random.choices(methods, weights=weights)[0]
                    data = None
                    if method == "POST":
                        data = gen_payload("json",512)
                    start = time.time()
                    async with session.request(method, url, data=data) as resp:
                        await resp.read()
                        latency = (time.time()-start)*1000
                        results.append((resp.status,latency,method))
                except Exception:
                    results.append(("ERR",0,"ERR"))
                finally:
                    sem.release()
            asyncio.create_task(do_req())
            await asyncio.sleep(interval)
        await asyncio.sleep(2)
        q.put(results)

# ---------- Process ----------
def process_main(proc_id, url, methods, weights, duration, per_proc_rps, concurrency, q):
    asyncio.run(worker(url, methods, weights, per_proc_rps, duration, concurrency, q))

# ---------- Summary ----------
def aggregate(all_results):
    latencies=[r[1] for r in all_results if r[0]!="ERR"]
    errors=sum(1 for r in all_results if r[0]=="ERR")
    total=len(all_results)
    statuses={}
    for r in all_results:
        statuses[r[0]]=statuses.get(r[0],0)+1
    summary={
        "total_requests":total,
        "errors":errors,
        "error_ratio":errors/total if total else 0,
        "avg_latency_ms":mean(latencies) if latencies else None,
        "median_latency_ms":median(latencies) if latencies else None,
        "min_latency_ms":min(latencies) if latencies else None,
        "max_latency_ms":max(latencies) if latencies else None,
        "status_counts":statuses,
    }
    print("\n📊 Kết quả:")
    for k,v in summary.items(): print(f"- {k}: {v}")

# ---------- Main ----------
def main():
    print("🔥 SUPER LOADTEST INPUT (NO UVLOOP) 🔥")
    url=input("Nhập URL (vd: https://example.com): ").strip()
    duration=int(input("Thời gian test (giây): ") or 30)
    rps=int(input("Sức mạnh RPS (requests/second): ") or 100)
    concurrency=int(input("Concurrency mỗi process: ") or 100)
    processes=int(input("Số process (mặc định dùng hết CPU core): ") or mp.cpu_count())

    # Method mix
    method_input=input("Chọn method (vd: GET,POST,HEAD) hoặc Enter để auto mix: ").strip().upper()
    if method_input:
        methods=method_input.split(",")
        weights=[1]*len(methods)
    else:
        methods=["GET","POST","HEAD"]
        weights=[70,20,10]  # mặc định mix

    per_proc_rps=rps/max(1,processes)
    q=mp.Queue(); procs=[]
    for i in range(processes):
        p=mp.Process(target=process_main,args=(i,url,methods,weights,duration,per_proc_rps,concurrency,q))
        p.start(); procs.append(p)
    all_results=[]
    for _ in range(processes): all_results.extend(q.get())
    for p in procs: p.join()
    aggregate(all_results)

if __name__=="__main__": main()
