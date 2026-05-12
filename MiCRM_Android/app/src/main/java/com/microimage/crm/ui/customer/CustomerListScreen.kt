package com.microimage.crm.ui.customer

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.microimage.crm.api.RetrofitClient
import com.microimage.crm.model.CustomerSummary
import com.microimage.crm.ui.Screen
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CustomerListScreen(token: String, navController: NavController) {
    val scope = rememberCoroutineScope()
    var customers by remember { mutableStateOf<List<CustomerSummary>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var userRole by remember { mutableStateOf("") }

    LaunchedEffect(Unit) {
        scope.launch {
            try {
                val authHeader = "Token $token"
                
                // 1. Get user role first
                val userRes = RetrofitClient.apiService.getCurrentUser(authHeader)
                if (userRes.isSuccessful) {
                    userRole = userRes.body()?.role ?: ""
                }

                // 2. Fetch customers based on role
                val response = if (userRole == "salesperson") {
                    RetrofitClient.apiService.getMyCustomers(authHeader)
                } else {
                    RetrofitClient.apiService.getCustomers(authHeader)
                }

                if (response.isSuccessful) {
                    customers = response.body() ?: emptyList()
                } else {
                    // If global list fails with 404, try the "mine" endpoint as a fallback
                    if (response.code() == 404) {
                        val fallbackRes = RetrofitClient.apiService.getMyCustomers(authHeader)
                        if (fallbackRes.isSuccessful) {
                            customers = fallbackRes.body() ?: emptyList()
                        } else {
                            errorMessage = "Error: ${response.code()}"
                        }
                    } else {
                        errorMessage = "Error: ${response.code()}"
                    }
                }
            } catch (e: Exception) {
                errorMessage = e.message
            } finally {
                isLoading = false
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Customers") },
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = {
                navController.navigate(Screen.CustomerCreateRequest.createRoute(token))
            }) {
                Icon(Icons.Default.Add, contentDescription = "Request New Customer")
            }
        }
    ) { padding ->
        Box(modifier = Modifier.padding(padding).fillMaxSize()) {
            if (isLoading) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            } else if (errorMessage != null) {
                Text(errorMessage!!, modifier = Modifier.align(Alignment.Center))
            } else if (customers.isEmpty()) {
                Text("No customers found", modifier = Modifier.align(Alignment.Center))
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(customers) { customer ->
                        CustomerCard(customer) {
                            navController.navigate(Screen.CustomerDetail.createRoute(token, customer.id))
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun CustomerCard(customer: CustomerSummary, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable { onClick() },
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = customer.companyName, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(text = customer.contactPersonName, style = MaterialTheme.typography.bodyMedium)
            Spacer(modifier = Modifier.height(4.dp))
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(text = customer.industry ?: "No Industry", style = MaterialTheme.typography.bodySmall, color = Color.Gray)
                Text(
                    text = customer.displayStatus ?: "Active",
                    style = MaterialTheme.typography.bodySmall,
                    color = if (customer.isActive) Color(0xFF2E7D32) else Color.Red
                )
            }
        }
    }
}
