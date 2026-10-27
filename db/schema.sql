-- QueryLens HR Schema: 8 tables, 3NF, InnoDB (needed for FKs + transactions)

CREATE DATABASE IF NOT EXISTS querylens_hr;
USE querylens_hr;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS query_log;
DROP TABLE IF EXISTS payroll;
DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS employee_projects;
DROP TABLE IF EXISTS projects;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS job_titles;
DROP TABLE IF EXISTS departments;
DROP TABLE IF EXISTS locations;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE locations (
    location_id     INT AUTO_INCREMENT PRIMARY KEY,
    city            VARCHAR(100) NOT NULL,
    state           VARCHAR(100) NOT NULL,
    country         VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE departments (
    department_id   INT AUTO_INCREMENT PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL UNIQUE,
    location_id     INT NOT NULL,
    FOREIGN KEY (location_id) REFERENCES locations(location_id)
) ENGINE=InnoDB;

CREATE TABLE job_titles (
    job_title_id    INT AUTO_INCREMENT PRIMARY KEY,
    title_name      VARCHAR(100) NOT NULL UNIQUE,
    min_salary      DECIMAL(10,2) NOT NULL,
    max_salary      DECIMAL(10,2) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE employees (
    employee_id     INT AUTO_INCREMENT PRIMARY KEY,
    first_name      VARCHAR(50) NOT NULL,
    last_name       VARCHAR(50) NOT NULL,
    email           VARCHAR(150) NOT NULL UNIQUE,
    hire_date       DATE NOT NULL,
    department_id   INT NOT NULL,
    job_title_id    INT NOT NULL,
    manager_id      INT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(department_id),
    FOREIGN KEY (job_title_id) REFERENCES job_titles(job_title_id),
    FOREIGN KEY (manager_id) REFERENCES employees(employee_id)
) ENGINE=InnoDB;

CREATE TABLE projects (
    project_id      INT AUTO_INCREMENT PRIMARY KEY,
    project_name    VARCHAR(150) NOT NULL,
    department_id   INT NOT NULL,
    start_date      DATE NOT NULL,
    end_date        DATE NULL,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
) ENGINE=InnoDB;

CREATE TABLE employee_projects (
    employee_id     INT NOT NULL,
    project_id      INT NOT NULL,
    role_on_project VARCHAR(100) NOT NULL,
    hours_allocated INT NOT NULL,
    PRIMARY KEY (employee_id, project_id),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
) ENGINE=InnoDB;

CREATE TABLE attendance (
    attendance_id   BIGINT AUTO_INCREMENT PRIMARY KEY,
    employee_id     INT NOT NULL,
    work_date       DATE NOT NULL,
    check_in        TIME NOT NULL,
    check_out       TIME NULL,
    status          ENUM('present','absent','half_day','leave') NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
) ENGINE=InnoDB;

CREATE TABLE payroll (
    payroll_id      INT AUTO_INCREMENT PRIMARY KEY,
    employee_id     INT NOT NULL,
    pay_period      DATE NOT NULL,
    base_salary     DECIMAL(10,2) NOT NULL,
    bonus           DECIMAL(10,2) NOT NULL DEFAULT 0,
    deductions      DECIMAL(10,2) NOT NULL DEFAULT 0,
    net_pay         DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
) ENGINE=InnoDB;

-- QueryLens's own log table (used later for transaction logging + undo)
CREATE TABLE query_log (
    log_id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    executed_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    nl_input        TEXT NOT NULL,
    generated_sql   TEXT NOT NULL,
    query_type      ENUM('SELECT','INSERT','UPDATE','DELETE') NOT NULL,
    affected_table  VARCHAR(100) NULL,
    before_image    JSON NULL,
    after_image     JSON NULL,
    status          ENUM('committed','rolled_back','undone') NOT NULL DEFAULT 'committed'
) ENGINE=InnoDB;
