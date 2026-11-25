resource "aws_sagemaker_model_package_group" "forecast" {
  model_package_group_name        = "${var.name_prefix}-forecast"
  model_package_group_description = "XGBoost 24-hour energy forecasting models awaiting approval."
  tags                            = local.tags
}

resource "aws_sagemaker_model_package_group" "anomaly" {
  model_package_group_name        = "${var.name_prefix}-anomaly"
  model_package_group_description = "Random Cut Forest hourly anomaly models awaiting approval."
  tags                            = local.tags
}
