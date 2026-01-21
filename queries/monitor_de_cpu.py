import psutil
import time
import threading
import csv
from datetime import datetime
from pathlib import Path

class CpuMonitor:
    def __init__(self, interval_us=1, log_file="cpu_monitor.csv"):
        """
        Inicializa o monitor de CPU.
        
        :param interval_us: Intervalo de atualização em microssegundos (padrão: 1 microssegundo).
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
        
        # Para cálculo preciso de CPU %
        self.last_cpu_times = None
        self.last_system_cpu_times = None
        
        # Verifica se o arquivo já existe e contém dados
        if not Path(self.log_file).exists() or Path(self.log_file).stat().st_size == 0:
            # Inicializa o arquivo CSV com cabeçalhos apenas se ele estiver vazio ou não existir
            with open(self.log_file, mode="a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["Timestamp", "Library", "Query", "PID", 
                               "Process_CPU_Percent", "Children_CPU_Percent", 
                               "Total_CPU_Percent", "System_CPU_Percent"])

    def _get_cpu_info(self):
        """
        Retorna o uso de CPU do processo, seus filhos e do sistema.
        """
        if self.pid is None:
            raise ValueError("PID não configurado.")

        try:
            process = psutil.Process(self.pid)

            # Usar interval=0.1 para a primeira medição funcionar
            process_cpu = process.cpu_percent(interval=0.1)  # ⬅️ MUDANÇA AQUI

            # CPU dos processos filhos
            children_cpu = 0
            for child in process.children(recursive=True):
                try:
                    # Também usar interval para filhos
                    children_cpu += child.cpu_percent(interval=None)  # Filhos podem usar None
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                
            total_cpu = process_cpu + children_cpu

            # Sistema também precisa de interval para primeira medição
            system_cpu = psutil.cpu_percent(interval=None)  # None funciona aqui após primeira

            return {
                "process_cpu": process_cpu,
                "children_cpu": children_cpu,
                "total_cpu": total_cpu,
                "system_cpu": system_cpu
            }
        except psutil.NoSuchProcess:
            return None

    def _monitor(self):
        """
        Monitora o uso de CPU em um loop contínuo enquanto `self.running` for True.
        """
        self.start_time = datetime.now()
        
        # Primeira leitura para inicializar as métricas
        time.sleep(0.1)  # Pequeno delay para primeira medição
        
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
            
            # Adiciona os dados ao arquivo CSV
            with open(self.log_file, mode="a", newline="" ) as file:
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
    
    def get_summary(self):
        """
        Retorna um resumo das métricas coletadas (útil para análise pós-execução).
        """
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

# Exemplo de uso
if __name__ == "__main__":
    # Exemplo básico de uso
    monitor = CpuMonitor(interval_us=500_000)  # 0.5 segundos
    
    # Configura o PID do processo atual
    monitor.set_pid(psutil.Process().pid)
    monitor.set_query_details(1, "polars-benchmark")
    
    print("Iniciando monitoramento de CPU...")
    monitor.start_monitoring()
    
    # Simula algum processamento
    for i in range(5):
        print(f"Processamento {i+1}...")
        # Simula carga de CPU
        _ = sum(x*x for x in range(10_000))
        time.sleep(1)
    
    print("Parando monitoramento...")
    monitor.stop_monitoring()
    
    print(monitor.get_summary())
    print(f"Dados salvos em: {monitor.log_file}")