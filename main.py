import os
import requests
from dotenv import load_dotenv
from terminaltables import AsciiTable


def get_page_json_vacancies(api_url, headers="", params=""):
    response = requests.get(api_url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def get_page_hh_json_vacancies(page, vacancy_text):
    moscow_code = 1
    max_vacancy_counts = 100
    params = {
            "text": f"NAME:{vacancy_text}",
            "area": moscow_code,
            "page": page,
            "per_page": max_vacancy_counts
        }
    api_hh_url = "https://api.hh.ru/vacancies"
    return get_page_json_vacancies(api_hh_url, params=params)


def get_page_sj_json_vacancies(page, vacancy_text):
    superjob_key = os.getenv("SUPERJOB_SEKRET_KEY")
    sj_headers = {"X-Api-App-Id": superjob_key}
    moscow_code = 4
    params = {
                    "keyword": vacancy_text,
                    "town": moscow_code,
                    "page": page
                }
    api_sj_url = "https://api.superjob.ru/2.0/vacancies/"
    return get_page_json_vacancies(api_sj_url, headers=sj_headers, params=params)


def predict_salary(salary_from, salary_to):

    if (not salary_from) and (not salary_to):
        return None

    if salary_from and (not salary_to):
        return int(int(salary_from) * 1.2)

    if (not salary_from) and salary_to:
        return int(int(salary_to) * 0.8)

    return int((int(salary_from) + int(salary_to)) / 2)


def predict_rub_salary_hh(vacancy):
    salary_vacancy = vacancy["salary"]
    return predict_salary(salary_vacancy["from"], salary_vacancy["to"])


def predict_rub_salary_sj(vacancy):
    if vacancy["currency"] != "rub":
        return None
    return predict_salary(vacancy["payment_from"], vacancy["payment_to"])


def get_average_salary_vacancy_table(salary_vacancies, title=""):
    output_table = []
    output_table.append(["Язык программирования",
                         "Вакансий найдено",
                         "Вакансий обработано",
                         "Средняя зарплата"
                         ])
    for programming_language, calculation_salary_vacancies in salary_vacancies.items():
        output_table.append([programming_language,
                            calculation_salary_vacancies["vacancies_found"],
                            calculation_salary_vacancies["vacancies_processed"],
                            calculation_salary_vacancies["average_salary"]])

    return AsciiTable(output_table, title).table


def main():
    load_dotenv()
    developer_languages = ["java", "python", "js", "ruby", "php", "c++", "c#"]

    vacancy_sj_language_counts = {}
    vacancy_hh_language_counts = {}

    for developer_language in developer_languages:
        sj_page = 0
        hh_page = 0
        salary_sj_vacancies = []
        salary_hh_vacancies = []

        # SJ get vacancy

        vacancy_more = True

        while vacancy_more:
            vacancies = get_page_sj_json_vacancies(sj_page, developer_language)

            for vacancy in vacancies["objects"]:
                vacancy_rub_salary_sj = predict_rub_salary_sj(vacancy)
                if vacancy_rub_salary_sj:
                    salary_sj_vacancies.append(vacancy_rub_salary_sj)

            if not salary_sj_vacancies:
                average_salary = 0
            else:
                average_salary = int(sum(salary_sj_vacancies) / len(salary_sj_vacancies))

            vacancy_sj_language_counts[developer_language] = {
                "vacancies_found": vacancies["total"],
                "vacancies_processed": len(salary_sj_vacancies),
                "average_salary": average_salary
            }
            vacancy_more = vacancies["more"]
            sj_page += 1

        # HH get vacancy

        while True:
            vacancies = get_page_hh_json_vacancies(hh_page, developer_language)

            vacancy_found = vacancies["found"]
            vacancy_pages = vacancies["pages"]

            for vacancy in vacancies["items"]:
                if (vacancy["salary"]) and (vacancy["salary"]["currency"] == "RUR"):
                    salary_hh_vacancies.append(predict_rub_salary_hh(vacancy))
            hh_page += 1
            if hh_page > vacancy_pages:
                break

        if not salary_hh_vacancies:
            average_salary = 0
        else:
            average_salary = int(sum(salary_hh_vacancies) / len(salary_hh_vacancies))

        vacancy_hh_language_counts[developer_language] = {
            "vacancies_found": vacancy_found,
            "vacancies_processed": len(salary_hh_vacancies),
            "average_salary": average_salary
        }

    print(get_average_salary_vacancy_table(vacancy_hh_language_counts,
                                           "-HeadHanter Moscow"))
    print()
    print(get_average_salary_vacancy_table(vacancy_sj_language_counts,
                                           "-SuperJob Moscow"))


if __name__ == "__main__":
    main()
