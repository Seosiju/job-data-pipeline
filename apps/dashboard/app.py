"""
잡코리아 채용시장 분석 대시보드

실행: streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# 페이지 설정
st.set_page_config(
    page_title="잡코리아 채용시장 분석",
    page_icon="📊",
    layout="wide"
)

# 환경변수 로드
load_dotenv()


@st.cache_resource
def get_db_connection():
    """DB 연결 (캐싱)"""
    db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    return create_engine(db_url)


@st.cache_data(ttl=300)
def load_data():
    """데이터 로드 (5분 캐싱)"""
    engine = get_db_connection()
    df_jobs = pd.read_sql('SELECT * FROM job_postings', engine)
    df_companies = pd.read_sql('SELECT * FROM companies', engine)
    df = df_jobs.merge(df_companies, left_on='company_id', right_on='id', suffixes=('', '_company'))
    return df, df_jobs, df_companies


@st.cache_data(ttl=300)
def load_analysis_data():
    """LLM 분석 데이터 로드"""
    engine = get_db_connection()

    # 분석 데이터 존재 여부 확인
    try:
        df_analysis = pd.read_sql('''
            SELECT jpa.*, jp.title, c.name as company_name
            FROM job_posting_analysis jpa
            JOIN job_postings jp ON jpa.job_posting_id = jp.id
            JOIN companies c ON jp.company_id = c.id
        ''', engine)

        # 스킬 집계
        required_skills = pd.read_sql('''
            SELECT skill, COUNT(*) as cnt
            FROM job_posting_analysis,
                 jsonb_array_elements_text(required_skills) as skill
            GROUP BY skill
            ORDER BY cnt DESC
        ''', engine)

        preferred_skills = pd.read_sql('''
            SELECT skill, COUNT(*) as cnt
            FROM job_posting_analysis,
                 jsonb_array_elements_text(preferred_skills) as skill
            GROUP BY skill
            ORDER BY cnt DESC
        ''', engine)

        return df_analysis, required_skills, preferred_skills
    except:
        return None, None, None


def normalize_location(loc):
    """지역 정규화"""
    if pd.isna(loc):
        return '기타'
    loc = str(loc).split(' 외')[0]
    parts = loc.split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1]}"
    return loc


def categorize_experience(exp):
    """경력 분류"""
    if pd.isna(exp):
        return '미표기'
    exp = str(exp)
    if '신입' in exp and '경력' in exp:
        return '신입/경력'
    elif '신입' in exp:
        return '신입'
    elif '경력무관' in exp:
        return '경력무관'
    elif '경력' in exp:
        import re
        match = re.search(r'(\d+)년', exp)
        if match:
            years = int(match.group(1))
            if years <= 3:
                return '경력 1-3년'
            elif years <= 5:
                return '경력 4-5년'
            else:
                return '경력 6년+'
        return '경력'
    return '기타'


def main():
    # 데이터 로드
    df, df_jobs, df_companies = load_data()

    # 데이터 전처리
    df['location_normalized'] = df['location'].apply(normalize_location)
    df['region'] = df['location_normalized'].apply(lambda x: x.split()[0] if pd.notna(x) else '기타')
    df['exp_category'] = df['experience'].apply(categorize_experience)

    # 헤더
    st.title("📊 잡코리아 채용시장 분석 대시보드")
    st.markdown("---")

    # KPI 카드
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 공고 수", f"{len(df_jobs):,}개")
    with col2:
        st.metric("총 회사 수", f"{len(df_companies):,}개")
    with col3:
        newbie_friendly = df['exp_category'].isin(['신입', '신입/경력', '경력무관']).sum()
        st.metric("신입 가능 공고", f"{newbie_friendly:,}개", f"{newbie_friendly/len(df)*100:.0f}%")
    with col4:
        keywords = df['search_keyword'].dropna().nunique()
        st.metric("검색 키워드", f"{keywords}개")

    st.markdown("---")

    # 사이드바 필터
    st.sidebar.header("🔍 필터")

    # 키워드 필터
    all_keywords = ['전체'] + sorted(df['search_keyword'].dropna().unique().tolist())
    selected_keyword = st.sidebar.selectbox("검색 키워드", all_keywords)

    # 회사 규모 필터
    all_sizes = ['전체'] + sorted(df['company_size'].dropna().unique().tolist())
    selected_size = st.sidebar.selectbox("회사 규모", all_sizes)

    # 경력 필터
    all_exp = ['전체'] + sorted(df['exp_category'].unique().tolist())
    selected_exp = st.sidebar.selectbox("경력 요구사항", all_exp)

    # 필터 적용
    filtered_df = df.copy()
    if selected_keyword != '전체':
        filtered_df = filtered_df[filtered_df['search_keyword'] == selected_keyword]
    if selected_size != '전체':
        filtered_df = filtered_df[filtered_df['company_size'] == selected_size]
    if selected_exp != '전체':
        filtered_df = filtered_df[filtered_df['exp_category'] == selected_exp]

    st.sidebar.markdown(f"**필터 결과: {len(filtered_df):,}개 공고**")

    # 메인 차트
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗺️ 지역별", "📈 경력별", "🏢 회사규모별", "🔑 키워드별", "🎯 스킬분석"])

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("광역시/도별 분포")
            region_counts = filtered_df['region'].value_counts().head(10)
            fig = px.bar(
                x=region_counts.values,
                y=region_counts.index,
                orientation='h',
                color=region_counts.values,
                color_continuous_scale='Blues'
            )
            fig.update_layout(showlegend=False, yaxis={'categoryorder': 'total ascending'})
            fig.update_xaxes(title="공고 수")
            fig.update_yaxes(title="")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("서울 구별 분포")
            seoul_df = filtered_df[filtered_df['region'] == '서울']
            if len(seoul_df) > 0:
                seoul_gu = seoul_df['location_normalized'].value_counts().head(10)
                fig = px.bar(
                    x=seoul_gu.values,
                    y=seoul_gu.index,
                    orientation='h',
                    color=seoul_gu.values,
                    color_continuous_scale='Oranges'
                )
                fig.update_layout(showlegend=False, yaxis={'categoryorder': 'total ascending'})
                fig.update_xaxes(title="공고 수")
                fig.update_yaxes(title="")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("서울 지역 데이터가 없습니다.")

    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("경력 요구사항 분포")
            exp_counts = filtered_df['exp_category'].value_counts()
            fig = px.pie(
                values=exp_counts.values,
                names=exp_counts.index,
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("경력별 공고 수")
            fig = px.bar(
                x=exp_counts.index,
                y=exp_counts.values,
                color=exp_counts.values,
                color_continuous_scale='Viridis'
            )
            fig.update_xaxes(title="경력 요구사항")
            fig.update_yaxes(title="공고 수")
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("회사 규모별 분포")
            size_counts = filtered_df['company_size'].value_counts()
            size_counts = size_counts[size_counts.index.notna() & (size_counts.index != '-')]
            fig = px.bar(
                x=size_counts.values,
                y=size_counts.index,
                orientation='h',
                color=size_counts.values,
                color_continuous_scale='Greens'
            )
            fig.update_layout(showlegend=False, yaxis={'categoryorder': 'total ascending'})
            fig.update_xaxes(title="회사 수")
            fig.update_yaxes(title="")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("회사 규모 x 경력 히트맵")
            heatmap_data = pd.crosstab(
                filtered_df['company_size'],
                filtered_df['exp_category'],
                normalize='index'
            ) * 100
            heatmap_data = heatmap_data.loc[heatmap_data.index.notna() & (heatmap_data.index != '-')]

            if len(heatmap_data) > 0:
                fig = px.imshow(
                    heatmap_data,
                    text_auto='.1f',
                    color_continuous_scale='YlOrRd',
                    aspect='auto'
                )
                fig.update_xaxes(title="경력 요구사항")
                fig.update_yaxes(title="회사 규모")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("데이터가 부족합니다.")

    with tab4:
        df_with_kw = filtered_df[filtered_df['search_keyword'].notna()]

        if len(df_with_kw) > 0:
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("키워드별 공고 수")
                kw_counts = df_with_kw['search_keyword'].value_counts()
                fig = px.bar(
                    x=kw_counts.index,
                    y=kw_counts.values,
                    color=kw_counts.values,
                    color_continuous_scale='Purples'
                )
                fig.update_xaxes(title="검색 키워드")
                fig.update_yaxes(title="공고 수")
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("키워드별 경력 분포")
                kw_exp = pd.crosstab(
                    df_with_kw['search_keyword'],
                    df_with_kw['exp_category'],
                    normalize='index'
                ) * 100
                fig = px.bar(
                    kw_exp,
                    barmode='stack',
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig.update_xaxes(title="검색 키워드")
                fig.update_yaxes(title="비율 (%)")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("키워드 데이터가 없습니다.")

    with tab5:
        # LLM 분석 데이터 로드
        df_analysis, required_skills, preferred_skills = load_analysis_data()

        if df_analysis is not None and len(df_analysis) > 0:
            st.subheader(f"📊 LLM 분석 결과 ({len(df_analysis)}개 공고)")

            # KPI 카드
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("분석 완료", f"{len(df_analysis)}개")
            with col2:
                multi = df_analysis['is_multi_position'].sum()
                st.metric("다중 포지션", f"{multi}개", f"{multi/len(df_analysis)*100:.0f}%")
            with col3:
                da_count = (df_analysis['job_category'] == '데이터분석').sum()
                st.metric("데이터분석 직무", f"{da_count}개")
            with col4:
                high_conf = (df_analysis['analysis_confidence'] == 'high').sum()
                st.metric("높은 신뢰도", f"{high_conf}개", f"{high_conf/len(df_analysis)*100:.0f}%")

            st.markdown("---")

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("🔧 필수 스킬 TOP 15")
                top_required = required_skills.head(15)
                fig = px.bar(
                    top_required,
                    x='cnt',
                    y='skill',
                    orientation='h',
                    color='cnt',
                    color_continuous_scale='Blues'
                )
                fig.update_layout(
                    showlegend=False,
                    yaxis={'categoryorder': 'total ascending'},
                    xaxis_title="등장 횟수",
                    yaxis_title=""
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("⭐ 우대 스킬 TOP 15")
                top_preferred = preferred_skills.head(15)
                fig = px.bar(
                    top_preferred,
                    x='cnt',
                    y='skill',
                    orientation='h',
                    color='cnt',
                    color_continuous_scale='Oranges'
                )
                fig.update_layout(
                    showlegend=False,
                    yaxis={'categoryorder': 'total ascending'},
                    xaxis_title="등장 횟수",
                    yaxis_title=""
                )
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("💼 직무 카테고리 분포")
                job_cat = df_analysis['job_category'].value_counts().head(10)
                fig = px.pie(
                    values=job_cat.values,
                    names=job_cat.index,
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("🏭 회사 도메인 분포")
                domain = df_analysis['company_domain'].value_counts().head(10)
                fig = px.pie(
                    values=domain.values,
                    names=domain.index,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)

            # 데이터분석 직무 상세
            st.markdown("---")
            st.subheader("🎯 데이터분석 직무 상세")

            da_df = df_analysis[df_analysis['job_category'] == '데이터분석']
            if len(da_df) > 0:
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.markdown(f"**총 {len(da_df)}개 공고**")
                    st.markdown("**채용 회사:**")
                    for _, row in da_df.iterrows():
                        st.markdown(f"- {row['company_name']}")

                with col2:
                    # 데이터분석 스킬
                    engine = get_db_connection()
                    da_skills = pd.read_sql('''
                        SELECT skill, COUNT(*) as cnt
                        FROM job_posting_analysis,
                             jsonb_array_elements_text(required_skills) as skill
                        WHERE job_category = '데이터분석'
                        GROUP BY skill
                        ORDER BY cnt DESC
                        LIMIT 10
                    ''', engine)

                    fig = px.bar(
                        da_skills,
                        x='skill',
                        y='cnt',
                        color='cnt',
                        color_continuous_scale='Viridis',
                        title="데이터분석 필수 스킬"
                    )
                    fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="등장 횟수")
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("데이터분석 직무 공고가 없습니다.")

        else:
            st.warning("LLM 분석 데이터가 없습니다. `python scripts/analyze_jd_with_llm.py`를 실행해주세요.")

    # 상세 데이터 테이블
    st.markdown("---")
    st.subheader("📋 상세 데이터")

    show_cols = ['title', 'name', 'location', 'experience', 'company_size', 'search_keyword']
    display_df = filtered_df[show_cols].rename(columns={
        'title': '공고 제목',
        'name': '회사명',
        'location': '지역',
        'experience': '경력',
        'company_size': '회사 규모',
        'search_keyword': '검색 키워드'
    })

    st.dataframe(display_df.head(100), use_container_width=True)

    # 푸터
    st.markdown("---")
    st.markdown("*데이터 출처: 잡코리아 크롤링 | 마지막 업데이트: 2026-03-16*")


if __name__ == "__main__":
    main()
