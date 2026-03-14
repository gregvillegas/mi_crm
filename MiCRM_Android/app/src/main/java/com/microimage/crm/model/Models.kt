package com.microimage.crm.model

import com.google.gson.annotations.SerializedName

data class User(
    @SerializedName("id") val id: Int,
    @SerializedName("username") val username: String,
    @SerializedName("email") val email: String,
    @SerializedName("first_name") val firstName: String,
    @SerializedName("last_name") val lastName: String,
    @SerializedName("role") val role: String
)

data class LoginResponse(
    @SerializedName("token") val token: String,
    @SerializedName("user_id") val userId: Int,
    @SerializedName("email") val email: String,
    @SerializedName("role") val role: String
)

data class LoginRequest(
    @SerializedName("username") val username: String,
    @SerializedName("password") val password: String
)

data class SalesFunnel(
    @SerializedName("id") val id: Int,
    @SerializedName("company_name") val companyName: String,
    @SerializedName("stage_display") val stage: String,
    @SerializedName("retail") val retail: Double,
    @SerializedName("probability") val probability: Int
)

data class Proposal(
    @SerializedName("id") val id: Int,
    @SerializedName("proposal_number") val proposalNumber: String,
    @SerializedName("subject") val subject: String,
    @SerializedName("customer_name") val customerName: String,
    @SerializedName("total_amount") val totalAmount: Double,
    @SerializedName("status_display") val status: String,
    @SerializedName("currency") val currency: String
)

data class ActivityType(
    @SerializedName("name") val name: String,
    @SerializedName("icon") val icon: String,
    @SerializedName("color") val color: String
)

data class SalesActivity(
    @SerializedName("id") val id: Int,
    @SerializedName("title") val title: String,
    @SerializedName("activity_type_details") val activityType: ActivityType?,
    @SerializedName("status_display") val status: String,
    @SerializedName("scheduled_start") val scheduledStart: String?,
    @SerializedName("customer_name") val customerName: String?
)
