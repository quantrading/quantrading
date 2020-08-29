from abc import ABCMeta, abstractmethod
from .simulation_result_utils import save_simulation_result_to_excel_file
from .. import utils


class BackTestBase(metaclass=ABCMeta):
    @abstractmethod
    def get_result(self):
        pass

    def result_to_excel(self, file_name=None, folder_path=None):
        if file_name is None:
            file_name = self.name

        if folder_path is None:
            path = f"./{file_name}.xlsx"
        else:
            utils.make_folder(f'./{folder_path}')
            path = f"./{folder_path}/{file_name}.xlsx"

        result = self.get_result()
        save_simulation_result_to_excel_file(result, path)

    def port_value_to_csv(self, file_name=None, folder_path=None):
        if file_name is None:
            file_name = self.name

        if folder_path is None:
            path = f"./{file_name}.csv"
        else:
            path = f"./{folder_path}/{file_name}.csv"

        result = self.get_result()
        performance = result['performance']
        portfolio_log = performance["portfolio_log"]
        port_value = portfolio_log['port_value']
        port_value.to_csv(path, encoding='cp949')
