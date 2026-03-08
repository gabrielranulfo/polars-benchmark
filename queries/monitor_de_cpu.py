import psutil
import time
import threading
import csv
from datetime import datetime
from pathlib import Path

class CpuMonitor:
    def __init__(self, interval_us=1, log_file="cpu_monitor.csv"):
        self.pid = None
        self.interval_us = interval_us
        self.interval_s = interval_us / 1e6
        self.running = False
        self.thread = None
        self.start_time = None
        self.end_time = None
        self.log_file = log_file
        self.query_number = None
        self.library_name = None

        self.last_proc_cpu = None
        self.last_children_cpu = {}
        self.last_sys_cpu = None

        if not Path(self.log_file).exists() or Path(self.log_file).stat().st_size == 0:
            with open(self.log_file, mode="a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([
                    "Timestamp",
                    "Library",
                    "Query",
                    "PID",
                    "Process_CPU_Percent",
                    "Children_CPU_Percent",
                    "Total_CPU_Percent",
                    "System_CPU_Percent"
                ])

    def _reset_baseline(self):
        self.last_proc_cpu = None
        self.last_children_cpu = {}
        self.last_sys_cpu = None

    def _get_cpu_info(self):
        if self.pid is None:
            raise ValueError("PID não configurado.")

        try:
            process = psutil.Process(self.pid)

            proc_times = process.cpu_times()
            proc_cpu_total = proc_times.user + proc_times.system

            sys_cpu = psutil.cpu_times()
            sys_total = sum(sys_cpu)

            if self.last_proc_cpu is None:
                self.last_proc_cpu = proc_cpu_total
                self.last_sys_cpu = sys_total

                for child in process.children(recursive=True):
                    try:
                        ct = child.cpu_times()
                        self.last_children_cpu[child.pid] = ct.user + ct.system
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                return {
                    "process_cpu": 0.0,
                    "children_cpu": 0.0,
                    "total_cpu": 0.0,
                    "system_cpu": psutil.cpu_percent(interval=None)
                }

            delta_proc = proc_cpu_total - self.last_proc_cpu
            delta_sys = sys_total - self.last_sys_cpu

            if delta_sys <= 0:
                return {
                    "process_cpu": 0.0,
                    "children_cpu": 0.0,
                    "total_cpu": 0.0,
                    "system_cpu": psutil.cpu_percent(interval=None)
                }

            cpu_count = psutil.cpu_count()

            process_cpu = (delta_proc / delta_sys) * cpu_count * 100

            children_cpu_delta = 0.0
            current_children = {}

            for child in process.children(recursive=True):
                try:
                    ct = child.cpu_times()
                    total = ct.user + ct.system
                    current_children[child.pid] = total

                    last = self.last_children_cpu.get(child.pid)
                    if last is not None:
                        delta = total - last
                        if delta > 0:
                            children_cpu_delta += delta

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            children_cpu = (children_cpu_delta / delta_sys) * cpu_count * 100

            self.last_children_cpu = current_children
            self.last_proc_cpu = proc_cpu_total
            self.last_sys_cpu = sys_total

            total_cpu = process_cpu + children_cpu
            system_cpu = psutil.cpu_percent(interval=None)

            return {
                "process_cpu": process_cpu,
                "children_cpu": children_cpu,
                "total_cpu": total_cpu,
                "system_cpu": system_cpu
            }

        except psutil.NoSuchProcess:
            return None

    def _monitor(self):
        self.start_time = datetime.now()

        while self.running:
            cpu_info = self._get_cpu_info()

            if cpu_info is None:
                with open(self.log_file, mode="a", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        self.library_name,
                        self.query_number,
                        self.pid,
                        "Process Not Found",
                        "-",
                        "-",
                        "-"
                    ])
                break

            with open(self.log_file, mode="a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                    self.library_name,
                    self.query_number,
                    self.pid,
                    f"{cpu_info['process_cpu']:.2f}",
                    f"{cpu_info['children_cpu']:.2f}",
                    f"{cpu_info['total_cpu']:.2f}",
                    f"{cpu_info['system_cpu']:.2f}"
                ])

            time.sleep(self.interval_s)

        self.end_time = datetime.now()

        with open(self.log_file, mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                self.end_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
                self.library_name,
                self.query_number,
                self.pid,
                "Monitoring Ended",
                "-",
                "-",
                "-"
            ])

    def set_pid(self, pid: int):
        self.pid = pid
        self._reset_baseline()

    def set_query_details(self, query_number: int, library_name: str):
        self.query_number = query_number
        self.library_name = library_name

    def start_monitoring(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor)
            self.thread.start()

    def stop_monitoring(self):
        if self.running:
            self.running = False
            self.thread.join()

    def get_summary(self):
        if not self.start_time or not self.end_time:
            return "Monitoramento não foi executado ou ainda está em execução."

        duration = (self.end_time - self.start_time).total_seconds()

        return f"""
        Resumo do Monitoramento de CPU:
        - Processo PID: {self.pid}
        - Biblioteca: {self.library_name}
        - Query: {self.query_number}
        - Duração: {duration:.2f} segundos
        - Arquivo de Log: {self.log_file}
        """

if __name__ == "__main__":
    monitor = CpuMonitor(interval_us=500_000)

    monitor.set_pid(psutil.Process().pid)
    monitor.set_query_details(1, "polars-benchmark")

    monitor.start_monitoring()

    for _ in range(5):
        _ = sum(x*x for x in range(10_000))
        time.sleep(1)

    monitor.stop_monitoring()