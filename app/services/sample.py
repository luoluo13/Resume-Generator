from __future__ import annotations


def blank_resume() -> dict:
    return {
        "schemaVersion": 1,
        "id": "",
        "meta": {"createdAt": "", "updatedAt": ""},
        "basics": {
            "name": "",
            "jobIntention": "",
            "phone": "",
            "email": "",
            "city": "",
            "available": "",
            "yearsOfExperience": "",
            "gender": "",
            "birth": "",
            "political": "",
            "photo": "",
        },
        "sections": [
            {"id": "sec_education", "type": "education", "title": "教育背景", "visible": True, "items": []},
            {"id": "sec_experience", "type": "experience", "title": "工作经历", "visible": True, "items": []},
            {"id": "sec_project", "type": "project", "title": "项目经历", "visible": True, "items": []},
            {"id": "sec_skills", "type": "skills", "title": "专业技能", "visible": True, "items": []},
        ],
        "theme": {
            "template": "classic",
            "accent": "#bf4a2e",
            "fontFamily": "SourceHanSansSC",
            "fontSize": 10.5,
            "lineHeight": 1.35,
            "pageMargin": 18,
            "columns": 1,
            "photoPosition": "right",
            "dividerStyle": "line",
            "density": "normal",
            "variants": {},
        },
    }


def sample_resume() -> dict:
    return {
        "schemaVersion": 1,
        "id": "default",
        "meta": {"createdAt": "", "updatedAt": ""},
        "basics": {
            "name": "陈亦然",
            "jobIntention": "高级后端开发工程师",
            "phone": "138-0000-0000",
            "email": "chenyiran@example.com",
            "city": "上海",
            "available": "一个月内",
            "yearsOfExperience": "5 年",
            "photo": "",
        },
        "sections": [
            {
                "id": "sec_summary",
                "type": "custom",
                "title": "个人简介",
                "visible": True,
                "items": [
                    {
                        "title": "自我评价",
                        "subtitle": "",
                        "start": "",
                        "end": "",
                        "highlights": [
                            "<p>5 年后端开发经验，长期负责高并发交易链路的架构设计与性能治理，"
                            "熟悉从需求拆解到上线运维的完整流程。</p>",
                            "<p>擅长用数据定位问题，主导的简历解析服务重构使 P95 延迟下降 <strong>74%</strong>，"
                            "并沉淀为团队通用组件。</p>",
                        ],
                    }
                ],
            },
            {
                "id": "sec_exp",
                "type": "experience",
                "title": "工作经历",
                "visible": True,
                "items": [
                    {
                        "company": "字节跳动",
                        "role": "后端开发工程师",
                        "location": "上海",
                        "start": "2021.07",
                        "end": "",
                        "current": True,
                        "highlights": [
                            "<p>主导简历解析服务重构，引入异步任务与多级缓存，P95 延迟从 "
                            "<strong>820ms</strong> 降至 <strong>210ms</strong>，单机吞吐提升 2.4 倍。</p>",
                            "<p>搭建接口级监控与告警体系，将线上问题平均定位时间从 40 分钟压缩到 8 分钟。</p>",
                            "<p>作为 4 人小组的技术负责人，负责方案评审与代码质量把关，季度需求按期交付率 100%。</p>",
                        ],
                    },
                    {
                        "company": "携程旅行网",
                        "role": "后端开发工程师",
                        "location": "上海",
                        "start": "2019.07",
                        "end": "2021.06",
                        "current": False,
                        "highlights": [
                            "<p>负责酒店订单系统的库存与价格模块，支撑日均 <strong>300 万</strong> 级订单请求。</p>",
                            "<p>设计订单状态机与补偿任务，将超卖类线上事故减少 90%。</p>",
                        ],
                    },
                ],
            },
            {
                "id": "sec_proj",
                "type": "project",
                "title": "项目经历",
                "visible": True,
                "items": [
                    {
                        "name": "简历智能生成平台",
                        "role": "技术负责人",
                        "start": "2023.03",
                        "end": "2023.10",
                        "tech": ["Python", "FastAPI", "Playwright", "PostgreSQL"],
                        "link": "",
                        "highlights": [
                            "<p>设计模板协议与导出管线，支持 PDF / PNG / DOCX 三种格式的一致输出，"
                            "模板可插拔扩展且无需改动业务代码。</p>",
                            "<p>构建 A4 实时预览与一页检测能力，帮助用户在编辑过程中即时发现内容超页问题。</p>",
                        ],
                    },
                    {
                        "name": "统一配置中心",
                        "role": "核心开发",
                        "start": "2022.04",
                        "end": "2022.11",
                        "tech": ["Java", "Spring Boot", "etcd", "Redis"],
                        "link": "",
                        "highlights": [
                            "<p>为 30+ 微服务提供配置发布与灰度能力，支持秒级推送与版本回滚。</p>",
                            "<p>引入变更审计与权限模型，配置误操作导致的故障下降至 0。</p>",
                        ],
                    },
                ],
            },
            {
                "id": "sec_edu",
                "type": "education",
                "title": "教育背景",
                "visible": True,
                "items": [
                    {
                        "school": "华东师范大学",
                        "degree": "本科",
                        "major": "计算机科学与技术",
                        "start": "2015.09",
                        "end": "2019.06",
                        "gpa": "3.8 / 4.0",
                        "courses": "数据结构、操作系统、计算机网络、数据库原理",
                    }
                ],
            },
            {
                "id": "sec_skill",
                "type": "skills",
                "title": "专业技能",
                "visible": True,
                "items": [
                    {"group": "后端", "tags": ["Python", "FastAPI", "Java", "MySQL", "Redis", "Kafka"]},
                    {"group": "工程", "tags": ["Docker", "Kubernetes", "CI/CD", "Playwright", "Git"]},
                    {"group": "语言", "tags": ["英语 CET-6", "普通话二级甲等"]},
                ],
            },
            {
                "id": "sec_award",
                "type": "awards",
                "title": "荣誉奖项",
                "visible": True,
                "items": [
                    {"name": "年度优秀员工", "issuer": "字节跳动", "date": "2023.12"},
                    {"name": "技术创新奖", "issuer": "携程旅行网", "date": "2020.11"},
                ],
            },
            {
                "id": "sec_cert",
                "type": "certificate",
                "title": "证书资质",
                "visible": True,
                "items": [
                    {"name": "系统架构设计师", "issuer": "工信部软考", "date": "2022.06"},
                    {"name": "AWS Certified Developer", "issuer": "Amazon", "date": "2021.09"},
                ],
            },
        ],
        "theme": {
            "template": "classic",
            "accent": "#bf4a2e",
            "fontFamily": "SourceHanSansSC",
            "fontSize": 10.5,
            "lineHeight": 1.35,
            "pageMargin": 18,
            "columns": 1,
            "photoPosition": "right",
            "dividerStyle": "line",
            "density": "normal",
            "variants": {},
        },
    }
