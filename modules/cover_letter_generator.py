"""
Cover Letter Generator module for personalized cover letter creation.
Uses LLM (Grok API) with template-based fallback.
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CoverLetterGenerator:
    """
    Generate personalized cover letters based on CV, job description,
    company information, and desired style.
    """

    # Pre-defined templates for different job roles
    TEMPLATES = {
        "it_support": {
            "name": "IT Support",
            "description": "Template for IT Support / Help Desk positions",
            "template": """
Yth. Tim Rekrutmen {company},

Saya tertarik untuk melamar posisi {job_title} di {company} berdasarkan informasi lowongan yang saya peroleh. Dengan latar belakang di bidang teknologi informasi dan pengalaman dalam memberikan dukungan teknis, saya yakin dapat memberikan kontribusi positif bagi tim Anda.

Selama {years_experience} tahun terakhir, saya telah mengembangkan keahlian dalam:
- Troubleshooting hardware dan software
- Instalasi dan konfigurasi sistem operasi (Windows, Linux)
- Manajemen jaringan dan keamanan dasar
- Dukungan pengguna dan pelatihan staf

Saya memiliki sertifikasi CompTIA A+ dan pengalaman langsung dengan ticketing system seperti Jira dan Zendesk. Saya juga terbiasa bekerja dalam tim dan berkomunikasi dengan pengguna dari berbagai tingkat teknis.

Saya sangat antusias untuk bergabung dengan {company} dan berkontribusi dalam memastikan infrastruktur TI berjalan dengan optimal. Saya percaya bahwa keterampilan dan dedikasi saya akan menjadi aset berharga bagi perusahaan.

Terima kasih atas waktu dan pertimbangan Anda. Saya berharap dapat mendiskusikan lebih lanjut kontribusi yang dapat saya berikan.

Hormat saya,
{Nama Kandidat}
"""
        },
        "developer": {
            "name": "Developer",
            "description": "Template for Developer / Software Engineer positions",
            "template": """
Yth. Tim Rekrutmen {company},

Saya menulis surat ini untuk menyatakan ketertarikan saya pada posisi {job_title} di {company}. Dengan latar belakang sebagai pengembang perangkat lunak dan pengalaman {years_experience} tahun dalam pengembangan aplikasi, saya yakin dapat memberikan nilai tambah bagi tim engineering Anda.

Keahlian teknis saya meliputi:
- Pengembangan backend menggunakan Python, Django, dan FastAPI
- Database management (PostgreSQL, MySQL, MongoDB)
- Containerization dengan Docker dan orchestration Kubernetes
- CI/CD pipelines menggunakan Jenkins dan GitLab CI
- Cloud platforms (AWS, GCP)

Saya sangat menikmati bekerja dalam tim agile dan memiliki pengalaman dalam code review, testing, dan deployment. Saya juga aktif berkontribusi pada open-source projects dan terus mengikuti perkembangan teknologi terbaru.

Saya tertarik dengan {company} karena reputasi perusahaan dalam inovasi teknologi dan komitmen terhadap kualitas produk. Saya percaya bahwa pengalaman dan semangat saya dalam pemecahan masalah akan sangat cocok dengan budaya kerja di {company}.

Saya sangat berharap dapat bertemu dengan Anda untuk mendiskusikan bagaimana saya dapat berkontribusi pada kesuksesan {company}.

Hormat saya,
{Nama Kandidat}
"""
        },
        "network_engineer": {
            "name": "Network Engineer",
            "description": "Template for Network Engineer positions",
            "template": """
Yth. Tim Rekrutmen {company},

Dengan hormat, saya mengajukan lamaran untuk posisi {job_title} di {company} yang saya ketahui melalui platform pencarian kerja. Dengan pengalaman {years_experience} tahun di bidang jaringan dan infrastruktur, saya siap untuk berkontribusi secara optimal.

Kualifikasi yang saya miliki antara lain:
- Perancangan dan implementasi jaringan enterprise
- Konfigurasi router dan switch (Cisco, Juniper)
- Firewall management dan keamanan jaringan
- Monitoring jaringan menggunakan SolarWinds, PRTG
- VLAN, VPN, dan routing protocols (OSPF, BGP)

Saya memiliki sertifikasi CCNA dan sedang mengejar CCNP. Saya terbiasa menangani proyek skala besar dan memiliki pengalaman dalam migrasi jaringan serta optimasi performa.

Saya melihat bahwa {company} adalah perusahaan yang dinamis dan memiliki infrastruktur jaringan yang kompleks. Saya sangat tertarik untuk bergabung dan membantu menjaga serta meningkatkan konektivitas dan keamanan jaringan perusahaan.

Demikian surat lamaran ini saya sampaikan. Atas perhatian dan pertimbangan Bapak/Ibu, saya ucapkan terima kasih.

Hormat saya,
{Nama Kandidat}
"""
        },
        "data_analyst": {
            "name": "Data Analyst",
            "description": "Template for Data Analyst / Data Scientist positions",
            "template": """
Yth. Tim Rekrutmen {company},

Saya dengan antusias melamar posisi {job_title} di {company}. Dengan latar belakang {years_experience} tahun dalam analisis data dan kecintaan saya pada data-driven decision making, saya percaya dapat memberikan dampak signifikan bagi perusahaan.

Kemampuan saya mencakup:
- Analisis data menggunakan Python (pandas, numpy, scikit-learn)
- Visualisasi data dengan Tableau dan Power BI
- SQL untuk data extraction dan manipulation
- Machine Learning dan predictive modeling
- Reporting dan dashboard creation

Saya memiliki pengalaman bekerja dengan big data dan mampu mengkomunikasikan insight kompleks kepada stakeholder non-teknis. Saya juga terbiasa dengan A/B testing dan optimasi produk berbasis data.

Saya tertarik dengan {company} karena pendekatan perusahaan yang berbasis data dalam pengambilan keputusan. Saya yakin bahwa keahlian analitis saya dapat membantu {company} dalam mengidentifikasi peluang bisnis dan meningkatkan efisiensi operasional.

Terima kasih atas waktu dan kesempatan yang diberikan. Saya berharap dapat berdiskusi lebih lanjut mengenai kontribusi saya untuk {company}.

Hormat saya,
{Nama Kandidat}
"""
        },
        "project_manager": {
            "name": "Project Manager",
            "description": "Template for Project Manager positions",
            "template": """
Yth. Tim Rekrutmen {company},

Saya menulis surat ini untuk menyatakan ketertarikan saya pada posisi {job_title} di {company}. Dengan pengalaman {years_experience} tahun dalam manajemen proyek dan kepemimpinan tim, saya yakin dapat membawa nilai tambah bagi organisasi Anda.

Kompetensi yang saya miliki:
- Manajemen proyek agile (Scrum, Kanban)
- Project planning dan scheduling
- Resource management dan budgeting
- Stakeholder communication dan reporting
- Risk management dan quality assurance

Saya memiliki sertifikasi PMP dan Scrum Master. Saya telah berhasil memimpin berbagai proyek dengan nilai hingga Rp 5 Miliar dan tim yang terdiri dari 10-20 orang.

Saya sangat tertarik dengan {company} dan visi perusahaan dalam inovasi. Saya percaya bahwa pendekatan saya yang terstruktur dan fokus pada hasil akan sangat cocok dengan kebutuhan {company}.

Demikian surat lamaran ini saya buat. Saya berharap dapat bergabung dan berkontribusi dalam kesuksesan {company}.

Hormat saya,
{Nama Kandidat}
"""
        },
        "general": {
            "name": "General",
            "description": "General template for any position",
            "template": """
Yth. Tim Rekrutmen {company},

Saya mengajukan lamaran untuk posisi {job_title} di {company} berdasarkan informasi lowongan yang saya peroleh. Dengan pengalaman {years_experience} tahun di bidang yang relevan, saya yakin dapat memberikan kontribusi positif.

Keahlian dan kompetensi yang saya miliki:
{skills_bullet}

Saya sangat antusias untuk bergabung dengan {company} dan berkontribusi pada kesuksesan perusahaan. Saya percaya bahwa kombinasi antara pengalaman, keterampilan, dan dedikasi saya akan menjadi aset berharga.

Terima kasih atas waktu dan pertimbangan Anda. Saya berharap dapat mendiskusikan lebih lanjut peluang ini.

Hormat saya,
{Nama Kandidat}
"""
        }
    }

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize CoverLetterGenerator.

        Args:
            db_path: Path to the SQLite database file. If None, uses default 'data/loker.db'.
        """
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            "loker.db"
        )
        self._ensure_database()

    def _ensure_database(self) -> None:
        """Ensure the database exists and has the required table."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cover_letters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    job_title TEXT,
                    company TEXT,
                    style TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _get_candidate_info(self, cv_text: str) -> Dict[str, Any]:
        """
        Extract candidate information from CV text.

        Args:
            cv_text: The CV text content

        Returns:
            Dictionary with candidate info (name, skills, experience)
        """
        info = {
            "name": "Nama Kandidat",
            "skills": [],
            "years_experience": 0,
            "summary": ""
        }

        # Simple extraction from CV text
        lines = cv_text.split('\n')
        for line in lines:
            line_lower = line.strip().lower()
            # Try to find name (simple heuristic)
            if "nama" in line_lower or "name" in line_lower:
                parts = line.split(':')
                if len(parts) > 1:
                    info["name"] = parts[1].strip()
            # Try to find experience
            if "tahun" in line_lower and ("pengalaman" in line_lower or "experience" in line_lower):
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    info["years_experience"] = int(numbers[0])

        # Extract skills from comma-separated lists
        for line in lines:
            line_lower = line.strip().lower()
            if "keahlian" in line_lower or "skills" in line_lower or "kompetensi" in line_lower:
                # Try to find skills after colon
                if ':' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        skills = parts[1].strip()
                        # Split by comma or semicolon
                        for sep in [',', ';', '•']:
                            if sep in skills:
                                info["skills"] = [s.strip() for s in skills.split(sep) if s.strip()]
                                break
                        else:
                            info["skills"] = [skills]
                        break

        return info

    def _generate_llm_prompt(
        self,
        cv_text: str,
        job_title: str,
        company: str,
        job_description: str,
        style: str
    ) -> str:
        """
        Generate a prompt for the LLM.

        Args:
            cv_text: CV content
            job_title: Job title
            company: Company name
            job_description: Job description
            style: Writing style (formal/semi-formal/creative)

        Returns:
            Prompt string
        """
        style_guidance = {
            "formal": "Gunakan bahasa Indonesia yang formal, sopan, dan profesional. Hindari bahasa gaul atau terlalu santai.",
            "semi-formal": "Gunakan bahasa Indonesia yang profesional namun sedikit lebih santai dan personal. Tetaplah sopan.",
            "creative": "Gunakan bahasa Indonesia yang kreatif dan menonjolkan kepribadian. Bisa menggunakan metafora atau gaya yang lebih engaging."
        }.get(style, "Gunakan bahasa Indonesia yang profesional.")

        prompt = f"""
Anda adalah asisten penulis surat lamaran kerja yang profesional. Buatkan surat lamaran (cover letter) yang dipersonalisasi berdasarkan informasi berikut:

INFORMASI KANDIDAT (CV):
{cv_text[:1500]}... (truncated if longer)

POSISI YANG DILAMAR:
{job_title}

PERUSAHAAN:
{company}

DESKRIPSI PEKERJAAN:
{job_description}

GAYA PENULISAN:
{style_guidance}

PETUNJUK:
1. Buat surat lamaran yang relevan dan personalisasi berdasarkan kualifikasi kandidat
2. Hubungkan pengalaman dan keahlian kandidat dengan kebutuhan posisi
3. Tunjukkan antusiasme terhadap perusahaan dan posisi
4. Surat harus terdiri dari 3-4 paragraf dengan struktur: pembukaan, isi (2 paragraf), penutup
5. Jangan mencantumkan data kontak palsu
6. Gunakan placeholder {{nama}} untuk nama kandidat jika tidak ada di CV
7. Output hanya surat lamaran tanpa tambahan komentar lain

SURAT LAMARAN:
"""
        return prompt

    def _generate_with_llm(
        self,
        cv_text: str,
        job_title: str,
        company: str,
        job_description: str,
        style: str
    ) -> Optional[str]:
        """
        Generate cover letter using LLM (Grok API).

        Returns:
            Generated cover letter or None if failed
        """
        try:
            # Try to import OpenAI client for Grok API
            from openai import OpenAI

            # Get API key from environment or config
            api_key = os.environ.get("GROK_API_KEY")
            if not api_key:
                # Try to read from config.json
                config_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    "config.json"
                )
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        api_key = config.get("grok_api_key")

            if not api_key:
                logger.warning("No Grok API key found, using template fallback")
                return None

            client = OpenAI(
                api_key=api_key,
                base_url="https://api.x.ai/v1"
            )

            prompt = self._generate_llm_prompt(
                cv_text, job_title, company, job_description, style
            )

            response = client.chat.completions.create(
                model="grok-beta",
                messages=[
                    {"role": "system", "content": "Anda adalah penulis surat lamaran profesional yang menghasilkan surat berkualitas tinggi."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )

            cover_letter = response.choices[0].message.content
            logger.info("Successfully generated cover letter using LLM")
            return cover_letter

        except ImportError:
            logger.warning("OpenAI library not installed, using template fallback")
            return None
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return None

    def _generate_from_template(
        self,
        cv_text: str,
        job_title: str,
        company: str,
        job_description: str,
        style: str
    ) -> str:
        """
        Generate cover letter using template-based approach.

        Args:
            cv_text: CV content
            job_title: Job title
            company: Company name
            job_description: Job description
            style: Writing style

        Returns:
            Generated cover letter
        """
        # Extract candidate info
        info = self._get_candidate_info(cv_text)

        # Determine which template to use
        template_key = "general"
        job_title_lower = job_title.lower()
        if "support" in job_title_lower or "help" in job_title_lower:
            template_key = "it_support"
        elif "developer" in job_title_lower or "engineer" in job_title_lower:
            if "network" in job_title_lower:
                template_key = "network_engineer"
            else:
                template_key = "developer"
        elif "analyst" in job_title_lower or "data" in job_title_lower:
            template_key = "data_analyst"
        elif "project" in job_title_lower or "manager" in job_title_lower:
            template_key = "project_manager"

        template_data = self.TEMPLATES.get(template_key, self.TEMPLATES["general"])
        template = template_data["template"]

        # Prepare skills bullet points
        skills_bullet = ""
        if info["skills"]:
            skills_bullet = "\n".join([f"- {skill}" for skill in info["skills"][:5]])
        else:
            skills_bullet = "- Keterampilan teknis dan profesional yang relevan"

        # Format template
        cover_letter = template.format(
            company=company or "perusahaan",
            job_title=job_title or "posisi yang dilamar",
            years_experience=info["years_experience"] or "3",
            skills_bullet=skills_bullet,
            Nama_Kandidat=info["name"]
        )

        return cover_letter.strip()

    def generate(
        self,
        cv_text: str,
        job_title: str,
        company: str,
        job_description: str,
        style: str = "formal"
    ) -> str:
        """
        Generate a personalized cover letter.

        Args:
            cv_text: The CV text content
            job_title: The job title being applied for
            company: The company name
            job_description: The job description text
            style: Writing style - 'formal', 'semi-formal', or 'creative'

        Returns:
            Generated cover letter as a string
        """
        if style not in ["formal", "semi-formal", "creative"]:
            style = "formal"
            logger.warning(f"Invalid style '{style}', defaulting to 'formal'")

        logger.info(f"Generating cover letter for {job_title} at {company} with style '{style}'")

        # Try LLM first
        cover_letter = self._generate_with_llm(
            cv_text, job_title, company, job_description, style
        )

        # Fallback to template
        if not cover_letter:
            cover_letter = self._generate_from_template(
                cv_text, job_title, company, job_description, style
            )
            logger.info("Used template-based generation as fallback")

        return cover_letter

    def save_cover_letter(
        self,
        job_id: str,
        content: str,
        job_title: Optional[str] = None,
        company: Optional[str] = None,
        style: Optional[str] = None
    ) -> int:
        """
        Save cover letter to database.

        Args:
            job_id: The job ID this cover letter is for
            content: The cover letter content
            job_title: The job title (optional)
            company: The company name (optional)
            style: The style used (optional)

        Returns:
            The ID of the saved record
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cover_letters (job_id, content, job_title, company, style)
                VALUES (?, ?, ?, ?, ?)
            """, (job_id, content, job_title, company, style))
            record_id = cursor.lastrowid
            conn.commit()
            conn.close()
            logger.info(f"Saved cover letter for job {job_id} with ID {record_id}")
            return record_id
        except Exception as e:
            logger.error(f"Failed to save cover letter: {e}")
            raise

    def get_cover_letter_by_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a saved cover letter by job ID.

        Args:
            job_id: The job ID

        Returns:
            Dictionary with cover letter data or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM cover_letters WHERE job_id = ?
                ORDER BY created_at DESC LIMIT 1
            """, (job_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve cover letter: {e}")
            return None

    def get_templates(self) -> List[Dict[str, str]]:
        """
        Get list of available cover letter templates.

        Returns:
            List of templates with name, description, and template preview
        """
        templates = []
        for key, template in self.TEMPLATES.items():
            templates.append({
                "id": key,
                "name": template["name"],
                "description": template["description"],
                "preview": template["template"][:200] + "..."
            })
        return templates

    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, str]]:
        """
        Get a specific template by ID.

        Args:
            template_id: The template ID (e.g., 'it_support', 'developer')

        Returns:
            Template dictionary or None if not found
        """
        if template_id in self.TEMPLATES:
            template = self.TEMPLATES[template_id]
            return {
                "id": template_id,
                "name": template["name"],
                "description": template["description"],
                "template": template["template"]
            }
        return None

    def get_cover_letter_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get the history of generated cover letters.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of cover letter records
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM cover_letters
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get cover letter history: {e}")
            return []


# Example usage
if __name__ == "__main__":
    # Test the generator
    generator = CoverLetterGenerator()

    cv_sample = """
Nama: John Doe
Keahlian: Python, SQL, Docker, Kubernetes, Git
Pengalaman: 5 tahun sebagai Software Engineer
    """

    cover_letter = generator.generate(
        cv_text=cv_sample,
        job_title="Senior Software Developer",
        company="TechCorp Indonesia",
        job_description="Membangun aplikasi web skala besar dengan Python dan cloud infrastructure.",
        style="formal"
    )

    print("Generated Cover Letter:")
    print("=" * 50)
    print(cover_letter)

    # Save it
    generator.save_cover_letter(
        job_id="job_12345",
        content=cover_letter,
        job_title="Senior Software Developer",
        company="TechCorp Indonesia",
        style="formal"
    )

    # List templates
    print("\nAvailable Templates:")
    for t in generator.get_templates():
        print(f"- {t['id']}: {t['name']} - {t['description']}")
