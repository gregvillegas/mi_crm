package com.microimage.crm.api

import com.microimage.crm.model.LoginRequest
import com.microimage.crm.model.LoginResponse
import com.microimage.crm.model.User
import com.microimage.crm.model.SalesFunnel
import com.microimage.crm.model.Proposal
import com.microimage.crm.model.SalesActivity
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

interface ApiService {
    @POST("api-token-auth/")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

    @GET("users/me/")
    suspend fun getCurrentUser(@Header("Authorization") token: String): Response<User>

    @GET("funnel/")
    suspend fun getSalesFunnel(@Header("Authorization") token: String): Response<List<SalesFunnel>>

    @GET("proposals/")
    suspend fun getProposals(@Header("Authorization") token: String): Response<List<Proposal>>

    @GET("activities/")
    suspend fun getSalesActivities(@Header("Authorization") token: String): Response<List<SalesActivity>>
}
