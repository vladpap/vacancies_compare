import os
import requests
from dotenv import load_dotenv
from terminaltables import AsciiTable


def get_page_json_vacancy(api_url, headers="", params=""):
    response = requests.get(api_url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def get_page_hh_json_vacancy(page, vacancy_text):
    params = {
            "text": f"NAME:{vacancy_text}",
            "area": 1,
            "page": page,
            "per_page": 100
        }
    api_hh_url = "https://api.hh.ru/vacancies"
    return get_page_json_vacancy(api_hh_url, params=params)


def get_page_sj_json_vacancy(page, vacancy_text):
    params = {
                    "keyword": vacancy_text,
                    "town": 4,
                    "page": page
                }
    api_sj_url = "https://api.superjob.ru/2.0/vacancies/"
    return get_page_json_vacancy(api_sj_url, headers=sj_headers, params=params)


def predict_salary(salary_from, salary_to):
    if salary_from:
        if salary_to:
            return int((int(salary_from) + int(salary_to)) / 2)
        else:
            return int(int(salary_from) * 1.2)
    else:
        if salary_to:
            return int(int(salary_to) * 0.8)
        else:
            return None


def predict_rub_salary_hh(vacancy):
    salary_vacancy = vacancy["salary"]
    return predict_salary(salary_vacancy["from"], salary_vacancy["to"])


def predict_rub_salary_sj(vacancy):
    if vacancy["currency"] != "rub":
        return None
    return predict_salary(vacancy["payment_from"], vacancy["payment_to"])


def get_average_salary_vacancy_table(salary_vacancys, title=""):
    output_table = []
    output_table.append(["Язык программирования",
                         "Вакансий найдено",
                         "Вакансий обработано",
                         "Средняя зарплата"
                         ])
    for language, item in salary_vacancys.items():
        output_table.append([language,
                            item["vacancies_found"],
                            item["vacancies_processed"],
                            item["average_salary"]])

    return AsciiTable(output_table, title).table


def main():
    vacancy_sj_language_counts = {}
    vacancy_hh_language_counts = {}

    for developer_language in developer_languages:
        sj_page = 0
        hh_page = 0
        vacancy_sj_predicts = []
        vacancy_hh_predicts = []
        
        # SJ get vacancy

        vacancy_more = True

        while vacancy_more:
            vacancys = get_page_sj_json_vacancy(sj_page, developer_language)

            for vacancy in vacancys["objects"]:
                predict_vacancy_rub_salary_sj = predict_rub_salary_sj(vacancy)
                if predict_vacancy_rub_salary_sj:
                    vacancy_sj_predicts.append(predict_vacancy_rub_salary_sj)

            if len(vacancy_sj_predicts) == 0:
                average_salary = 0
            else:
                average_salary = int(sum(vacancy_sj_predicts) / len(vacancy_sj_predicts))

            vacancy_sj_language_counts[developer_language] = {
                "vacancies_found": vacancys["total"],
                "vacancies_processed": len(vacancy_sj_predicts),
                "average_salary": average_salary
            }
            vacancy_more = vacancys["more"]
            sj_page += 1

        # HH get vacancy

        while True:
            json_hh_response = get_page_hh_json_vacancy(hh_page, developer_language)

            vacancy_found = json_hh_response["found"]
            vacancy_pages = json_hh_response["pages"]

            for vacancy in json_hh_response["items"]:
                if (vacancy["salary"]) and (vacancy["salary"]["currency"] == "RUR"):
                    vacancy_hh_predicts.append(predict_rub_salary_hh(vacancy))
            hh_page += 1
            if hh_page > vacancy_pages:
                break

        if len(vacancy_hh_predicts) == 0:
            average_salary = 0
        else:
            average_salary = int(sum(vacancy_hh_predicts) / len(vacancy_hh_predicts))

        vacancy_hh_language_counts[developer_language] = {
            "vacancies_found": vacancy_found,
            "vacancies_processed": len(vacancy_hh_predicts),
            "average_salary": average_salary
        }

    print(get_average_salary_vacancy_table(vacancy_hh_language_counts,
                                           "-HeadHanter Moscow"))
    print()
    print(get_average_salary_vacancy_table(vacancy_sj_language_counts,
                                           "-SuperJob Moscow"))


if __name__ == "__main__":
    load_dotenv()
    superjob_key = os.getenv("SUPERJOB_SEKRET_KEY")
    sj_headers = {"X-Api-App-Id": superjob_key}

    developer_languages = ["js", "java", "python", "ruby", "php", "c++", "c#"]
    main()
