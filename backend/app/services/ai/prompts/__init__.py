"""AI prompt templates — re-export from submodules for backward compatibility."""

# Agent system prompts
from app.services.ai.prompts.product_prompts import INVENTORY_AGENT_SYSTEM
from app.services.ai.prompts.customer_prompts import CUSTOMER_AGENT_SYSTEM

# Customer intelligence
from app.services.ai.prompts.customer_prompts import (
    rfm_prompt,
    churn_risk_prompt,
    followup_suggestion_prompt,
    followup_analysis_prompt,
    followup_recognition_prompt,
    customer_recognition_prompt,
    alert_enrichment_prompt,
)

# Product intelligence
from app.services.ai.prompts.product_prompts import (
    PRODUCT_AGENT_SYSTEM,
    product_parse_prompt,
    bom_parse_prompt,
    substitute_prompt,
    supplier_match_prompt,
    pricing_recommend_prompt,
    product_profile_prompt,
    spec_normalize_prompt,
    product_association_prompt,
    procurement_optimize_prompt,
    lifecycle_warning_prompt,
)

# Brand intelligence
from app.services.ai.prompts.brand_prompts import (
    brand_profile_prompt,
    brand_import_prompt,
    brand_portfolio_prompt,
    brand_compare_prompt,
    brand_health_prompt,
    brand_risk_prompt,
    brand_supplier_matrix_prompt,
    brand_recommendation_prompt,
)

# Brand product performance
from app.services.ai.prompts.brand_perf_prompts import (
    brand_product_performance_prompt,
    brand_customer_penetration_prompt,
    brand_lifecycle_prompt,
    brand_price_trends_prompt,
)

# Sales intelligence
from app.services.ai.prompts.sales_prompts import (
    quote_assist_prompt,
    watchtower_prompt,
    customer_product_matching_prompt,
    product_customer_matching_prompt,
)

# Supplier intelligence
from app.services.ai.prompts.supplier_prompts import (
    supplier_scorecard_prompt,
    supplier_delay_prediction_prompt,
    supplier_alternatives_prompt,
    supplier_price_variance_prompt,
    supplier_360_prompt,
    supplier_negotiation_prompt,
    supplier_comparison_prompt,
)

# Purchase order intelligence
from app.services.ai.prompts.po_prompts import (
    po_optimization_prompt,
    po_auto_suggest_prompt,
    po_risk_assessment_prompt,
)

# Finance intelligence
from app.services.ai.prompts.finance_prompts import (
    payment_prediction_prompt,
    cash_flow_forecast_prompt,
    dunning_strategy_prompt,
    credit_risk_prompt,
)

# Sales target intelligence
from app.services.ai.prompts.target_prompts import (
    target_recommendation_prompt,
    attainment_prediction_prompt,
    target_early_warning_prompt,
)

# Visit intelligence
from app.services.ai.prompts.visit_prompts import (
    visit_report_prompt,
    visit_sentiment_prompt,
    visit_effectiveness_prompt,
)

# Ticket intelligence
from app.services.ai.prompts.ticket_prompts import (
    ticket_classify_prompt,
    ticket_response_prompt,
    ticket_resolution_prediction_prompt,
    ticket_cluster_prompt,
)

# Contract intelligence
from app.services.ai.prompts.contract_prompts import (
    contract_extract_prompt,
    contract_risk_prompt,
    contract_expiry_prompt,
    contract_rebate_prompt,
)

# Multi-agent orchestration
from app.services.ai.prompts.orchestration_prompts import (
    orchestrate_customer_prompt,
    orchestrate_product_prompt,
    orchestrate_global_prompt,
)

# NLP query and sales enrichment
from app.services.ai.prompts.nlp_prompts import (
    nlp_query_prompt,
    opportunity_enrich_prompt,
    quotation_enrich_prompt,
    sales_order_enrich_prompt,
    delivery_note_enrich_prompt,
    list_risk_summary_prompt,
    quotation_list_enrich_prompt,
    order_list_enrich_prompt,
    delivery_list_enrich_prompt,
    flow_validate_quote_to_order_prompt,
    flow_validate_order_to_delivery_prompt,
)

__all__ = [
    "INVENTORY_AGENT_SYSTEM",
    "CUSTOMER_AGENT_SYSTEM",
    "PRODUCT_AGENT_SYSTEM",
    "rfm_prompt",
    "churn_risk_prompt",
    "followup_suggestion_prompt",
    "followup_analysis_prompt",
    "followup_recognition_prompt",
    "customer_recognition_prompt",
    "alert_enrichment_prompt",
    "product_parse_prompt",
    "bom_parse_prompt",
    "substitute_prompt",
    "supplier_match_prompt",
    "pricing_recommend_prompt",
    "product_profile_prompt",
    "spec_normalize_prompt",
    "product_association_prompt",
    "procurement_optimize_prompt",
    "lifecycle_warning_prompt",
    "brand_profile_prompt",
    "brand_import_prompt",
    "brand_portfolio_prompt",
    "brand_compare_prompt",
    "brand_health_prompt",
    "brand_risk_prompt",
    "brand_supplier_matrix_prompt",
    "brand_recommendation_prompt",
    "brand_product_performance_prompt",
    "brand_customer_penetration_prompt",
    "brand_lifecycle_prompt",
    "brand_price_trends_prompt",
    "quote_assist_prompt",
    "watchtower_prompt",
    "customer_product_matching_prompt",
    "product_customer_matching_prompt",
    "supplier_scorecard_prompt",
    "supplier_delay_prediction_prompt",
    "supplier_alternatives_prompt",
    "supplier_price_variance_prompt",
    "supplier_360_prompt",
    "supplier_negotiation_prompt",
    "supplier_comparison_prompt",
    "po_optimization_prompt",
    "po_auto_suggest_prompt",
    "po_risk_assessment_prompt",
    "payment_prediction_prompt",
    "cash_flow_forecast_prompt",
    "dunning_strategy_prompt",
    "credit_risk_prompt",
    "target_recommendation_prompt",
    "attainment_prediction_prompt",
    "target_early_warning_prompt",
    "visit_report_prompt",
    "visit_sentiment_prompt",
    "visit_effectiveness_prompt",
    "ticket_classify_prompt",
    "ticket_response_prompt",
    "ticket_resolution_prediction_prompt",
    "ticket_cluster_prompt",
    "contract_extract_prompt",
    "contract_risk_prompt",
    "contract_expiry_prompt",
    "contract_rebate_prompt",
    "orchestrate_customer_prompt",
    "orchestrate_product_prompt",
    "orchestrate_global_prompt",
    "nlp_query_prompt",
    "opportunity_enrich_prompt",
    "quotation_enrich_prompt",
    "sales_order_enrich_prompt",
    "delivery_note_enrich_prompt",
    "list_risk_summary_prompt",
    "quotation_list_enrich_prompt",
    "order_list_enrich_prompt",
    "delivery_list_enrich_prompt",
    "flow_validate_quote_to_order_prompt",
    "flow_validate_order_to_delivery_prompt",
]
