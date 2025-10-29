import psutil
import time
import threading
import csv
from datetime import datetime
from pathlib import Path

class MemoryMonitor:
    def __init__(self, interval_us=1_000_000, log_file="memory_monitor.csv"):
        """
        Inicializa o monitor de memória.

        :param interval_us: Intervalo de atualização em microssegundos (padrão: 1 segundo).
        :param log_file: Nome do arquivo CSV para salvar os logs.
        """
        self.pid = None  # O PID será configurado dinamicamente
        self.interval_us = interval_us
        self.interval_s = interval_us / 1e6  # Converte microssegundos para segundos
        self.running = False
        self.thread = None
        self.start_time = None
        self.end_time = None
        self.log_file = log_file
        self.query_number = None
        self.library_name = None

        # Verifica se o arquivo já existe e contém dados
        if not Path(self.log_file).exists() or Path(self.log_file).stat().st_size == 0:
            # Inicializa o arquivo CSV com cabeçalhos apenas se ele estiver vazio ou não existir
            with open(self.log_file, mode="a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["Timestamp", "Library", "Query", "PID", "Process_Memory_MB", "Children_Memory_MB", "Total_Memory_MB"])

    def _get_memory_info(self):
        """
        Retorna o uso de memória do processo e de seus filhos.
        """
        if self.pid is None:
            raise ValueError("PID não configurado. Configure o PID antes de iniciar o monitoramento.")

        try:
            process = psutil.Process(self.pid)
            memory_info = process.memory_info().rss
            children_memory = sum(child.memory_info().rss for child in process.children(recursive=True))
            total_memory = memory_info + children_memory
            return {
                "process_memory": memory_info / (1024 ** 2),  # Convertendo para MB
                "children_memory": children_memory / (1024 ** 2),  # Convertendo para MB
                "total_memory": total_memory / (1024 ** 2),  # Convertendo para MB
            }
        except psutil.NoSuchProcess:
            return None

    def _monitor(self):
        """
        Monitora o uso de memória em um loop contínuo enquanto `self.running` for True.
        """
        self.start_time = datetime.now()

        while self.running:
            memory_info = self._get_memory_info()
            if memory_info is None:
                with open(self.log_file, mode="a", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                        self.library_name,
                        self.query_number,
                        self.pid,
                        "Process Not Found",
                        "-",
                        "-"
                    ])
                break

            # Adiciona os dados ao arquivo CSV
            with open(self.log_file, mode="a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                    self.library_name,
                    self.query_number,
                    self.pid,
                    f"{memory_info['process_memory']:.2f}",
                    f"{memory_info['children_memory']:.2f}",
                    f"{memory_info['total_memory']:.2f}"
                ])

            time.sleep(self.interval_s)

        self.end_time = datetime.now()
        # Registra a finalização no CSV
        with open(self.log_file, mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                self.end_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
                self.library_name,
                self.query_number,
                self.pid,
                "Monitoring Ended",
                "-",
                "-"
            ])

    def set_pid(self, pid: int):
        """
        Configura dinamicamente o PID do processo a ser monitorado.
        """
        self.pid = pid

    def set_query_details(self, query_number: int, library_name: str):
        """
        Configura dinamicamente o número da query e o nome da biblioteca para log.
        """
        self.query_number = query_number
        self.library_name = library_name

    def start_monitoring(self):
        """
        Inicia o monitoramento em uma nova thread.
        """
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor)
            self.thread.start()

    def stop_monitoring(self):
        """
        Para o monitoramento e aguarda o término da thread.
        """
        if self.running:
            self.running = False
            self.thread.join()
