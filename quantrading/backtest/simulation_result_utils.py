import empyrical
import pandas as pd
from xlsxwriter.utility import xl_col_to_name
from .. import performance_utils


def save_simulation_result_to_excel_file(result: dict, path: str, insert_value_chart=False,
                                         compare_with_bench=False) -> None:
    performance = result['performance']
    event_log = result.get('event_log', None)
    rebalancing_weight = result.get('rebalancing_weight', None)
    order_weight = result.get('order_weight', None)
    portfolio_weight_history_df = result.get('portfolio_weight_history', None)

    portfolio_log = performance["portfolio_log"]
    monthly_returns = performance["monthly_returns"]
    annual_summary = performance["annual_summary"]
    performance_summary = performance["performance_summary"]
    returns_until_next_rebal = performance.get('returns_until_next_rebal', None)

    with pd.ExcelWriter(path, datetime_format="yyyy-mm-dd") as writer:
        portfolio_log.to_excel(writer, sheet_name="portfolio log")
        monthly_returns.to_excel(writer, sheet_name="월별수익률")
        annual_summary.to_excel(writer, sheet_name="연도별 요약")
        performance_summary.to_excel(writer, sheet_name="요약")

        workbook = writer.book

        if event_log is not None and len(event_log) > 0:
            event_log.to_excel(writer, sheet_name="event log")
        
        if order_weight is not None:
            order_weight.to_excel(writer, sheet_name="주문 비중")

        if returns_until_next_rebal is not None:
            returns_until_next_rebal.to_excel(writer, sheet_name="리밸간 수익률")

        if insert_value_chart:
            sheet_name = 'portfolio log'
            worksheet = writer.sheets[sheet_name]

            chart = workbook.add_chart({'type': 'line'})

            for i in range(len(performance_summary.columns)):
                col = i + 1
                chart.add_series({
                    'name': [sheet_name, 0, col],
                    'categories': [sheet_name, 1, 0, len(portfolio_log), 0],
                    'values': [sheet_name, 1, col, len(portfolio_log), col],
                })

            chart.set_x_axis({'name': 'strategy'})
            chart.set_y_axis({'name': 'value', 'major_gridlines': {'visible': True}})

            chart.set_legend({'position': 'bottom'})

            worksheet.insert_chart('B2', chart)

        percentge_styles = {
            'num_format': '0.00%',
        }

        float_styles = {
            'num_format': '0.00',
        }

        worksheet = writer.sheets['요약']
        percentge_format = workbook.add_format(percentge_styles)
        float_format = workbook.add_format(float_styles)

        columns_alphabet = xl_col_to_name(len(performance_summary.columns)) if type(
            performance_summary) is pd.DataFrame else xl_col_to_name(1)

        worksheet.conditional_format(f'B4:{columns_alphabet}7', {'type': 'cell',
                                                                 'criteria': '>=',
                                                                 'value': -999,
                                                                 'format': percentge_format})
        worksheet.conditional_format(f'B8:{columns_alphabet}8', {'type': 'cell',
                                                                 'criteria': '>=',
                                                                 'value': -999,
                                                                 'format': float_format})

        if compare_with_bench:
            # 벤치마크가 첫 자산
            benchmark_series = portfolio_log.iloc[:, 0]
            strategies_ratio_df = portfolio_log.divide(benchmark_series, axis=0)

            start_col = len(portfolio_log.columns) + 3
            strategies_ratio_df.to_excel(writer, sheet_name="portfolio log", startrow=0,
                                         startcol=start_col)

            workbook = writer.book
            sheet_name = 'portfolio log'
            worksheet = writer.sheets[sheet_name]

            chart = workbook.add_chart({'type': 'line'})

            for i in range(len(strategies_ratio_df.columns)):
                col = i + start_col + 1
                chart.add_series({
                    'name': [sheet_name, 0, col],
                    'categories': [sheet_name, 1, start_col, len(portfolio_log), start_col],
                    'values': [sheet_name, 1, col, len(portfolio_log), col],
                })

            chart.set_x_axis({'name': 'strategy'})
            chart.set_y_axis({'name': 'value', 'major_gridlines': {'visible': True}})

            chart.set_legend({'position': 'bottom'})

            worksheet.insert_chart(f'{xl_col_to_name(start_col + 5)}2', chart)

        portfolio_log['port_value'].to_excel(writer, sheet_name="value_history")

        if portfolio_weight_history_df is not None:
            portfolio_weight_history_df.to_excel(writer, sheet_name="weight_history")

        if rebalancing_weight is not None and len(rebalancing_weight) > 0:
            rebalancing_weight.to_excel(writer, sheet_name="rebalancing_history")


def calc_performance_from_value_history(daily_values: pd.Series) -> dict:
    daily_returns = daily_values.pct_change()
    final_returns = daily_values.iloc[-1] / 100 - 1

    monthly_returns = empyrical.aggregate_returns(daily_returns, "monthly")
    yearly_returns = empyrical.aggregate_returns(daily_returns, "yearly")
    performance_summary = performance_utils.get_performance_summary(daily_returns, final_returns)

    annual_std = performance_utils.get_annual_std(daily_returns)
    annual_summary = pd.concat([yearly_returns, annual_std], axis=1)
    annual_summary.columns = ["수익률", "변동성"]

    cumulative_returns = performance_utils.convert_values_to_cumulative_returns(daily_values)
    drawdown = performance_utils.get_draw_down(cumulative_returns)

    return {
        "monthly_returns": monthly_returns,
        "yearly_returns": yearly_returns,
        "performance_summary": performance_summary,
        "annual_summary": annual_summary,
        "drawdown": drawdown
    }