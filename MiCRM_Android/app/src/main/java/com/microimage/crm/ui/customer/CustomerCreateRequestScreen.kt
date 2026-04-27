package com.microimage.crm.ui.customer

import android.widget.Toast
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.microimage.crm.api.RetrofitClient
import com.microimage.crm.model.CustomerCreateRequestPayload
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CustomerCreateRequestScreen(token: String, navController: NavController) {
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val scrollState = rememberScrollState()

    var companyName by remember { mutableStateOf("") }
    var contactPersonName by remember { mutableStateOf("") }
    var contactPersonPosition by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var phoneNumber by remember { mutableStateOf("") }
    var address by remember { mutableStateOf("") }
    var industry by remember { mutableStateOf("") }
    var territory by remember { mutableStateOf("") }
    
    var isSubmitting by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Request New Customer") },
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .padding(16.dp)
                .fillMaxSize()
                .verticalScroll(scrollState),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            OutlinedTextField(
                value = companyName,
                onValueChange = { companyName = it },
                label = { Text("Company Name *") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = contactPersonName,
                onValueChange = { contactPersonName = it },
                label = { Text("Contact Person Name *") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = contactPersonPosition,
                onValueChange = { contactPersonPosition = it },
                label = { Text("Contact Position") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = email,
                onValueChange = { email = it },
                label = { Text("Email *") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = phoneNumber,
                onValueChange = { phoneNumber = it },
                label = { Text("Phone Number") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = address,
                onValueChange = { address = it },
                label = { Text("Address") },
                modifier = Modifier.fillMaxWidth(),
                minLines = 2
            )
            OutlinedTextField(
                value = industry,
                onValueChange = { industry = it },
                label = { Text("Industry") },
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = territory,
                onValueChange = { territory = it },
                label = { Text("Territory") },
                modifier = Modifier.fillMaxWidth()
            )

            Button(
                onClick = {
                    if (companyName.isBlank() || contactPersonName.isBlank() || email.isBlank()) {
                        Toast.makeText(context, "Please fill required fields", Toast.LENGTH_SHORT).show()
                        return@Button
                    }
                    
                    isSubmitting = true
                    scope.launch {
                        try {
                            val payload = CustomerCreateRequestPayload(
                                companyName = companyName,
                                contactPersonName = contactPersonName,
                                contactPersonPosition = contactPersonPosition.takeIf { it.isNotBlank() },
                                email = email,
                                phoneNumber = phoneNumber.takeIf { it.isNotBlank() },
                                address = address.takeIf { it.isNotBlank() },
                                industry = industry.takeIf { it.isNotBlank() },
                                territory = territory.takeIf { it.isNotBlank() }
                            )
                            val response = RetrofitClient.apiService.createCustomerRequest("Token $token", payload)
                            if (response.isSuccessful) {
                                Toast.makeText(context, "Request submitted successfully", Toast.LENGTH_LONG).show()
                                navController.popBackStack()
                            } else {
                                Toast.makeText(context, "Failed: ${response.code()}", Toast.LENGTH_SHORT).show()
                            }
                        } catch (e: Exception) {
                            Toast.makeText(context, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
                        } finally {
                            isSubmitting = false
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth().height(56.dp),
                enabled = !isSubmitting
            ) {
                if (isSubmitting) {
                    CircularProgressIndicator(color = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.size(24.dp))
                } else {
                    Text("Submit Request")
                }
            }
        }
    }
}
