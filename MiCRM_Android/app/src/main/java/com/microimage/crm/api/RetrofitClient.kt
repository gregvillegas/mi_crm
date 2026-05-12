package com.microimage.crm.api

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitClient {
    private var _baseUrl: String = "http://10.20.20.2:8001/api/v1/"
    val baseUrl: String get() = _baseUrl
    
    private var retrofit: Retrofit? = null

    fun updateBaseUrl(newHost: String) {
        val formattedHost = if (!newHost.startsWith("http")) "http://$newHost" else newHost
        val finalUrl = if (!formattedHost.endsWith("/")) "$formattedHost/" else formattedHost
        val finalApiUrl = if (!finalUrl.endsWith("api/v1/")) "${finalUrl}api/v1/" else finalUrl
        
        if (this._baseUrl != finalApiUrl) {
            this._baseUrl = finalApiUrl
            this.retrofit = null // Reset retrofit instance to recreate with new URL
        }
    }

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val httpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .build()

    private fun buildRetrofit(): Retrofit {
        return Retrofit.Builder()
            .baseUrl(_baseUrl)
            .addConverterFactory(GsonConverterFactory.create())
            .client(httpClient)
            .build()
    }

    val apiService: ApiService
        get() {
            if (retrofit == null) {
                retrofit = buildRetrofit()
            }
            return retrofit!!.create(ApiService::class.java)
        }
}
