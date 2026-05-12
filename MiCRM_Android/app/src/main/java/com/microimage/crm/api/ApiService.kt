package com.microimage.crm.api

import com.microimage.crm.model.LoginRequest
import com.microimage.crm.model.LoginResponse
import com.microimage.crm.model.User
import com.microimage.crm.model.SalesFunnel
import com.microimage.crm.model.Proposal
import com.microimage.crm.model.ProposalCreatePayload
import com.microimage.crm.model.ProposalDetail
import com.microimage.crm.model.PendingApproval
import com.microimage.crm.model.ApprovalDecisionPayload
import com.microimage.crm.model.SalesActivity
import com.microimage.crm.model.SalesActivityCreatePayload
import com.microimage.crm.model.CustomerSummary
import com.microimage.crm.model.CustomerDetail
import com.microimage.crm.model.CustomerCreateRequestPayload
import com.microimage.crm.model.CustomerRequest
import com.microimage.crm.model.CampaignSummary
import com.microimage.crm.model.CampaignPreview
import com.microimage.crm.model.ApiMessage
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path

interface ApiService {
    @POST("api-token-auth/")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

    @GET("users/me/")
    suspend fun getCurrentUser(@Header("Authorization") token: String): Response<User>

    @GET("funnel/")
    suspend fun getSalesFunnel(@Header("Authorization") token: String): Response<List<SalesFunnel>>

    @GET("customers/")
    suspend fun getCustomers(@Header("Authorization") token: String): Response<List<CustomerSummary>>

    @GET("customers/mine/")
    suspend fun getMyCustomers(@Header("Authorization") token: String): Response<List<CustomerSummary>>

    @GET("customers/{id}/")
    suspend fun getCustomerDetail(
        @Header("Authorization") token: String,
        @Path("id") customerId: Int
    ): Response<CustomerDetail>

    @POST("customer-requests/")
    suspend fun createCustomerRequest(
        @Header("Authorization") token: String,
        @Body request: CustomerCreateRequestPayload
    ): Response<CustomerRequest>

    @GET("customer-requests/mine/")
    suspend fun getMyCustomerRequests(@Header("Authorization") token: String): Response<List<CustomerRequest>>

    @GET("customer-requests/pending/")
    suspend fun getPendingCustomerRequests(@Header("Authorization") token: String): Response<List<CustomerRequest>>

    @POST("customer-requests/{id}/approve/")
    suspend fun approveCustomerRequest(
        @Header("Authorization") token: String,
        @Path("id") requestId: Int
    ): Response<Map<String, Any>>

    @POST("customer-requests/{id}/reject/")
    suspend fun rejectCustomerRequest(
        @Header("Authorization") token: String,
        @Path("id") requestId: Int,
        @Body payload: Map<String, String>
    ): Response<Map<String, Any>>

    @GET("proposals/")
    suspend fun getProposals(@Header("Authorization") token: String): Response<List<Proposal>>

    @GET("proposals/{id}/")
    suspend fun getProposalDetail(
        @Header("Authorization") token: String,
        @Path("id") proposalId: Int
    ): Response<ProposalDetail>

    @POST("proposals/")
    suspend fun createProposal(
        @Header("Authorization") token: String,
        @Body request: ProposalCreatePayload
    ): Response<ProposalDetail>

    @GET("proposals/pending_approvals/")
    suspend fun getPendingProposalApprovals(@Header("Authorization") token: String): Response<List<PendingApproval>>

    @POST("proposals/{id}/approve/")
    suspend fun approveProposal(
        @Header("Authorization") token: String,
        @Path("id") proposalId: Int,
        @Body request: ApprovalDecisionPayload
    ): Response<Map<String, Any>>

    @POST("proposals/{id}/reject/")
    suspend fun rejectProposal(
        @Header("Authorization") token: String,
        @Path("id") proposalId: Int,
        @Body request: ApprovalDecisionPayload
    ): Response<Map<String, Any>>

    @GET("activities/")
    suspend fun getSalesActivities(@Header("Authorization") token: String): Response<List<SalesActivity>>

    @POST("activities/")
    suspend fun createSalesActivity(
        @Header("Authorization") token: String,
        @Body request: SalesActivityCreatePayload
    ): Response<SalesActivity>

    @GET("campaigns/")
    suspend fun getCampaigns(@Header("Authorization") token: String): Response<List<CampaignSummary>>

    @GET("campaigns/{id}/preview/")
    suspend fun previewCampaign(
        @Header("Authorization") token: String,
        @Path("id") campaignId: Int
    ): Response<CampaignPreview>

    @POST("campaigns/{id}/send/")
    suspend fun sendCampaign(
        @Header("Authorization") token: String,
        @Path("id") campaignId: Int
    ): Response<ApiMessage>

    @POST("campaigns/{id}/cancel/")
    suspend fun cancelCampaign(
        @Header("Authorization") token: String,
        @Path("id") campaignId: Int
    ): Response<ApiMessage>
}
